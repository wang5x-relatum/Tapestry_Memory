"""Unit coverage for the public model, boundaries, and storage lifecycle."""
import math
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import UUID
from datetime import datetime

from tapestry_memory import Edge, MemoryStore, Node, RetrievalResult


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.addCleanup(self.store.close)

    def test_node_model_and_detached_metadata(self):
        metadata = {"provenance": {"pages": [1, 2], "uri": "file:原稿"}}
        node = self.store.add_node("a" * 1001, metadata=metadata, weight=0)
        self.assertIsInstance(node, Node)
        self.assertEqual(UUID(node.id).version, 4)
        self.assertEqual(datetime.fromisoformat(node.created_at).utcoffset().total_seconds(), 0)
        self.assertEqual(len(node.content), 1001)
        metadata["provenance"]["pages"].append(3)
        node.metadata["provenance"]["pages"].append(4)
        self.assertEqual(self.store.get_node(node.id).metadata["provenance"]["pages"], [1, 2])
        changed = self.store.update_node(node.id, content="", metadata={"x": 1}, weight=2)
        self.assertEqual(changed.id, node.id)
        self.assertEqual(changed.created_at, node.created_at)
        self.assertEqual(changed.metadata, {"x": 1})
        self.assertEqual(changed.weight, 2)
        self.assertNotEqual(self.store.add_node("").id, changed.id)

    def test_namespace_validation_and_binding(self):
        for value in (None, "", " \t", 4, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MemoryStore(namespace=value)
        self.assertEqual(self.store.namespace, "default")
        with self.assertRaises(AttributeError):
            self.store.namespace = "other"
        with MemoryStore(namespace=" x ") as other:
            self.assertEqual(other.namespace, " x ")

    def test_numeric_and_text_validation(self):
        for weight in (-1, math.nan, math.inf, -math.inf, True, "1", 10**1000):
            with self.subTest(weight=str(weight)[:20]), self.assertRaises(ValueError):
                self.store.add_node("x", weight=weight)
        with self.assertRaises(ValueError):
            self.store.add_node(None)
        node = self.store.add_node("x")
        for count in (0, -1, 1.0, True, 2**63):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.store.add_edge(node.id, node.id, "self", count=count)
        for value in (None, "", " "):
            with self.assertRaises(ValueError):
                self.store.get_node(value)
            with self.assertRaises(ValueError):
                self.store.add_edge(node.id, node.id, value)
        with self.assertRaises(KeyError):
            self.store.update_node("missing", weight=2)

    def test_strict_json(self):
        cycle = []
        cycle.append(cycle)
        for value in ([1], {1: "key"}, {"v": (1, 2)}, {"v": {1}},
                      {"v": math.nan}, {"v": object()}, {"v": cycle}):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                self.store.add_node("x", metadata=value)
        shared = {"key": [None, True, 2, 1.25, "你好"]}
        data = {"a": shared, "b": shared}
        self.assertEqual(self.store.add_node("x", metadata=data).metadata, data)

    def test_edge_upsert_direction_and_delete(self):
        left, right = self.store.add_node("a"), self.store.add_node("b")
        edge = self.store.add_edge(left.id, right.id, "cites", count=2)
        self.assertIsInstance(edge, Edge)
        updated = self.store.add_edge(left.id, right.id, "cites", count=5, weight=0.2)
        self.assertEqual(updated.created_at, edge.created_at)
        self.assertEqual(updated.count, 5)
        self.assertEqual(updated.weight, 0.2)
        self.assertIsNone(self.store.get_edge(right.id, left.id, "cites"))
        self.assertTrue(self.store.delete_edge(left.id, right.id, "cites"))
        self.assertFalse(self.store.delete_edge(left.id, right.id, "cites"))
        restored = self.store.add_edge(left.id, right.id, "cites")
        self.assertEqual(restored.created_at, edge.created_at)
        with self.assertRaises(KeyError):
            self.store.add_edge(left.id, "missing", "cites")

    def test_bfs_order_depth_budget_and_top_k(self):
        root = self.store.add_node("root")
        children = sorted([self.store.add_node("child") for _ in range(4)], key=lambda n: n.id)
        for child in reversed(children):
            self.store.add_edge(root.id, child.id, "child")
        leaf = self.store.add_node("leaf")
        self.store.add_edge(children[0].id, leaf.id, "next")
        result = self.store.retrieve([root.id, root.id, "absent"], max_depth=1)
        self.assertIsInstance(result, RetrievalResult)
        self.assertEqual(result.nodes, (root, *children))
        self.assertEqual(result.traversed_edges, 4)
        self.assertFalse(result.budget_exhausted)
        exact = self.store.retrieve([root.id], max_depth=1, traversal_budget=4)
        self.assertFalse(exact.budget_exhausted)
        limited = self.store.retrieve([root.id], traversal_budget=2)
        self.assertEqual(limited.nodes, (root, *children[:2]))
        self.assertEqual(limited.traversed_edges, 2)
        self.assertTrue(limited.budget_exhausted)
        capped = self.store.retrieve([root.id], top_k=1)
        self.assertEqual(capped.nodes, (root,))
        self.assertEqual(capped.visited_count, 6)
        self.assertEqual(capped.traversed_edges, 5)
        self.assertEqual(self.store.retrieve([root.id], top_k=0).nodes, ())
        zero = self.store.retrieve([root.id], traversal_budget=0)
        self.assertTrue(zero.budget_exhausted)
        self.assertEqual(zero.traversed_edges, 0)
        self.assertFalse(self.store.retrieve([root.id], max_depth=0, traversal_budget=0).budget_exhausted)
        self.assertFalse(self.store.retrieve([leaf.id], traversal_budget=0).budget_exhausted)

    def test_cycles_and_multiple_relations_are_charged(self):
        root = self.store.add_node("root")
        self.store.add_edge(root.id, root.id, "a")
        self.store.add_edge(root.id, root.id, "b")
        limited = self.store.retrieve([root.id], traversal_budget=1)
        self.assertEqual(limited.visited_count, 1)
        self.assertEqual(limited.traversed_edges, 1)
        self.assertTrue(limited.budget_exhausted)
        exact = self.store.retrieve([root.id], traversal_budget=2)
        self.assertFalse(exact.budget_exhausted)

    def test_retrieval_validation(self):
        for name in ("top_k", "max_depth", "traversal_budget"):
            for value in (-1, True, 1.5, None):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.store.retrieve([], **{name: value})
        for seeds in ("id", None, [None], [""]):
            with self.assertRaises(ValueError):
                self.store.retrieve(seeds)

    def test_delete_incident_edges_and_no_resurrection(self):
        nodes = [self.store.add_node(str(i)) for i in range(3)]
        self.store.add_edge(nodes[0].id, nodes[1].id, "out")
        self.store.add_edge(nodes[2].id, nodes[0].id, "in")
        self.store.add_edge(nodes[0].id, nodes[0].id, "self")
        self.assertTrue(self.store.delete_node(nodes[0].id))
        self.assertFalse(self.store.delete_node(nodes[0].id))
        self.assertIsNone(self.store.get_node(nodes[0].id))
        self.assertIsNone(self.store.get_edge(nodes[2].id, nodes[0].id, "in"))
        self.assertIsNone(self.store.get_edge(nodes[0].id, nodes[1].id, "out"))
        self.assertEqual(self.store.retrieve([nodes[0].id]).nodes, ())
        with self.assertRaises(KeyError):
            self.store.add_edge(nodes[2].id, nodes[0].id, "in")

    def test_nested_transactions_and_rollback(self):
        with self.store.transaction():
            kept = self.store.add_node("kept")
            with self.assertRaises(RuntimeError):
                with self.store.transaction():
                    dropped = self.store.add_node("dropped")
                    self.store.update_node(kept.id, content="changed")
                    raise RuntimeError("inner")
            self.assertIsNone(self.store.get_node(dropped.id))
            self.assertEqual(self.store.get_node(kept.id).content, "kept")
            with self.assertRaises(KeyError):
                self.store.add_edge(kept.id, "foreign", "bad")
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.store.delete_node(kept.id)
                with self.store.transaction():
                    rolled_back = self.store.add_node("inner committed")
                raise RuntimeError("outer")
        self.assertIsNotNone(self.store.get_node(kept.id))
        self.assertIsNone(self.store.get_node(rolled_back.id))

    def test_reopen_and_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.sqlite"
            with MemoryStore(path, namespace="a") as a, MemoryStore(path, namespace="b") as b:
                first = a.add_node("same", metadata={"provenance": ["source", {"part": 2}]})
                second = b.add_node("same")
                self.assertIsNone(a.get_node(second.id))
                self.assertFalse(a.delete_node(second.id))
                with self.assertRaises(KeyError):
                    a.add_edge(first.id, second.id, "cross")
                with self.assertRaises(RuntimeError):
                    with a.transaction():
                        failed = a.add_node("failed")
                        raise RuntimeError()
            with MemoryStore(path, namespace="a") as a, MemoryStore(path, namespace="b") as b:
                self.assertEqual(a.get_node(first.id), first)
                self.assertIsNone(a.get_node(failed.id))
                self.assertEqual(b.get_node(second.id), second)

    def test_reject_unrelated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "other.sqlite"
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE unrelated (value TEXT)")
            with self.assertRaises(ValueError):
                MemoryStore(path)
            with sqlite3.connect(path) as connection:
                names = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                self.assertEqual(names, [("unrelated",)])

    def test_close_and_context_semantics(self):
        with self.store.transaction():
            with self.assertRaises(RuntimeError):
                self.store.close()
        self.store.close()
        self.store.close()
        with self.assertRaises(RuntimeError):
            self.store.get_node("missing")
        with self.assertRaises(RuntimeError):
            self.store.add_node("closed")


if __name__ == "__main__":
    unittest.main()
