"""Independent public-API acceptance: six contracts plus four safeguards.

Tests use only disposable databases, never host/application memory files.
The dependency safeguard reads package source only for static import inspection.
"""

import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tapestry_memory import Edge, MemoryStore, Node, RetrievalResult


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "contract.sqlite3"

    def store(self, namespace="default"):
        store = MemoryStore(self.path, namespace=namespace)
        self.addCleanup(store.close)
        return store

    @staticmethod
    def ids(result):
        return tuple(node.id for node in result.nodes)


class AcceptanceContracts(StoreCase):
    """Exactly the six required standalone acceptance contracts."""

    def test_01_identical_content_has_independent_namespace_identity(self):
        a, b = self.store("A"), self.store("B")
        content = "same content / 相同内容 " * 100
        original = {"provenance": {"source": "local:合同", "lines": [1, 2]}}
        a_node = a.add_node(content, metadata=original, weight=0.5)
        b_node = b.add_node(content, metadata=original, weight=0.5)
        duplicate = a.add_node(content, metadata=original)
        self.assertNotEqual(a_node.id, duplicate.id)
        self.assertEqual(a_node.content, content)  # No inherited 500-char truncation.
        changed = a.update_node(
            a_node.id, content="changed A", metadata={"replacement": True}, weight=3.0
        )
        self.assertIsInstance(changed, Node)
        self.assertEqual(changed.id, a_node.id)
        self.assertEqual(changed.created_at, a_node.created_at)
        self.assertEqual(changed.metadata, {"replacement": True})
        self.assertEqual(changed.weight, 3.0)
        self.assertEqual(a.get_node(duplicate.id), duplicate)
        self.assertEqual(b.get_node(b_node.id), b_node)
        self.assertIsNone(a.get_node(b_node.id))
        self.assertIsNone(b.get_node(a_node.id))
        with self.assertRaises(KeyError):
            a.update_node(b_node.id, content="foreign overwrite")
        b.update_node(b_node.id, content="changed B", weight=0)
        self.assertEqual(a.get_node(a_node.id), changed)
        self.assertEqual(b.get_node(b_node.id).content, "changed B")

    def test_02_cross_edge_traversal_never_leaves_namespace(self):
        a, b = self.store("A"), self.store("B")
        a_nodes = [a.add_node(text) for text in ("seed", "middle", "end")]
        b_nodes = [b.add_node(text) for text in ("seed", "middle", "end")]
        for store, nodes in ((a, a_nodes), (b, b_nodes)):
            store.add_edge(nodes[0].id, nodes[1].id, "next")
            store.add_edge(nodes[1].id, nodes[2].id, "next")
            store.add_edge(nodes[2].id, nodes[0].id, "cycle")
        # UUIDs are assigned by the public API: there is deliberately no direct
        # SQL insertion of matching IDs or private-connection manipulation.
        for source, target in (
            (a_nodes[0].id, b_nodes[1].id),
            (b_nodes[0].id, a_nodes[1].id),
            (b_nodes[0].id, b_nodes[1].id),
        ):
            with self.subTest(source=source, target=target):
                with self.assertRaises(KeyError):
                    a.add_edge(source, target, "hostile")
                self.assertIsNone(a.get_edge(source, target, "hostile"))
        for store, own, foreign in ((a, a_nodes, b_nodes), (b, b_nodes, a_nodes)):
            result = store.retrieve(
                [foreign[0].id, own[0].id, own[0].id], max_depth=8
            )
            self.assertIsInstance(result, RetrievalResult)
            self.assertIsInstance(result.nodes, tuple)
            self.assertEqual(self.ids(result), tuple(node.id for node in own))
            self.assertEqual(result.visited_count, 3)
            self.assertEqual(result.traversed_edges, 3)
            self.assertFalse(result.budget_exhausted)
            self.assertEqual(store.retrieve([foreign[0].id]).nodes, ())

    def test_03_deleting_a_preserves_b_nodes_edges_and_provenance(self):
        a, b = self.store("A"), self.store("B")
        provenance = {"provenance": {"uri": "urn:原始材料", "spans": [[0, 10]]}}
        a_nodes = [a.add_node(x, metadata=provenance) for x in ("first", "second")]
        b_nodes = [b.add_node(x, metadata=provenance) for x in ("first", "second")]
        for store, nodes in ((a, a_nodes), (b, b_nodes)):
            store.add_edge(nodes[0].id, nodes[1].id, "forward", weight=0.25, count=4)
            store.add_edge(nodes[1].id, nodes[0].id, "backward")
            store.add_edge(nodes[0].id, nodes[0].id, "self")
        b_edges = [
            b.get_edge(b_nodes[0].id, b_nodes[1].id, "forward"),
            b.get_edge(b_nodes[1].id, b_nodes[0].id, "backward"),
            b.get_edge(b_nodes[0].id, b_nodes[0].id, "self"),
        ]
        # Warm retrieval before deletion to catch stale package-owned caches.
        self.assertEqual(len(a.retrieve([a_nodes[0].id]).nodes), 2)
        self.assertFalse(a.delete_node(b_nodes[0].id))
        self.assertFalse(a.delete_edge(b_nodes[0].id, b_nodes[1].id, "forward"))
        self.assertTrue(a.delete_node(a_nodes[0].id))
        self.assertFalse(a.delete_node(a_nodes[0].id))
        self.assertIsNone(a.get_edge(a_nodes[0].id, a_nodes[1].id, "forward"))
        self.assertIsNone(a.get_edge(a_nodes[1].id, a_nodes[0].id, "backward"))
        self.assertIsNone(a.get_edge(a_nodes[0].id, a_nodes[0].id, "self"))
        self.assertEqual(self.ids(a.retrieve([a_nodes[1].id])), (a_nodes[1].id,))
        self.assertTrue(a.delete_node(a_nodes[1].id))
        self.assertEqual(a.retrieve([node.id for node in a_nodes]).nodes, ())
        a.close()
        b.close()
        a, b = self.store("A"), self.store("B")
        for node in a_nodes:
            self.assertIsNone(a.get_node(node.id))
        self.assertEqual(a.retrieve([node.id for node in a_nodes]).nodes, ())
        self.assertEqual(tuple(b.get_node(node.id) for node in b_nodes), tuple(b_nodes))
        self.assertEqual(b.retrieve([b_nodes[0].id]).nodes, tuple(b_nodes))
        for edge in b_edges:
            self.assertEqual(b.get_edge(edge.source, edge.target, edge.relation), edge)

    def test_04_exception_rolls_back_nodes_and_edges_after_reopen(self):
        store = self.store()
        baseline = store.add_node("baseline", metadata={"provenance": ["durable"]})
        peer = store.add_node("peer")
        existing_edge = store.add_edge(baseline.id, peer.id, "existing", count=2)
        rolled_back_ids = []
        with self.assertRaisesRegex(RuntimeError, "abort outer"):
            with store.transaction():
                transient = store.add_node("must disappear")
                rolled_back_ids.append(transient.id)
                store.add_edge(baseline.id, transient.id, "transient")
                store.update_node(baseline.id, content="must revert", metadata={})
                store.add_edge(baseline.id, peer.id, "existing", weight=8, count=9)
                with store.transaction():
                    nested = store.add_node("inner commit is not outer commit")
                    rolled_back_ids.append(nested.id)
                    store.add_edge(transient.id, nested.id, "nested")
                raise RuntimeError("abort outer")
        self.assertEqual(store.get_node(baseline.id), baseline)
        for node_id in rolled_back_ids:
            self.assertIsNone(store.get_node(node_id))
        store.close()
        reopened = self.store()
        self.assertEqual(reopened.get_node(baseline.id), baseline)
        self.assertEqual(reopened.get_node(peer.id), peer)
        self.assertEqual(reopened.get_edge(baseline.id, peer.id, "existing"), existing_edge)
        self.assertIsNone(reopened.get_edge(baseline.id, rolled_back_ids[0], "transient"))
        self.assertIsNone(reopened.get_edge(*rolled_back_ids, "nested"))
        for node_id in rolled_back_ids:
            self.assertIsNone(reopened.get_node(node_id))
        self.assertEqual(reopened.retrieve([baseline.id]).nodes, (baseline, peer))

    def test_05_json_provenance_roundtrips_losslessly(self):
        metadata = {
            "provenance": {
                "sources": [
                    {"uri": "file:///不存在/原始 资料.txt", "span": [0, 37], "quote": "汉字 é é \n\t\x00"},
                    {"uri": "https://example.invalid/not-fetched", "attributes": {"verified": False, "note": None}},
                ],
                "nested": [[], {}, [True, False, None, 0, -7, 1.25, 2**63 + 19]],
                "empty": "",
            },
            "arbitrary": {"中文键": ["λ", "終"]},
        }
        store = self.store("provenance")
        original = store.add_node("original", metadata=metadata)
        plain = store.add_node("no provenance needed")
        store.add_edge(original.id, plain.id, "references")
        self.assertEqual(original.metadata, metadata)
        self.assertEqual(plain.metadata, {})
        store.close()
        reopened = self.store("provenance")
        fetched = reopened.get_node(original.id)
        retrieved = reopened.retrieve([original.id]).nodes[0]
        self.assertEqual(fetched, original)
        self.assertEqual(retrieved.metadata, metadata)
        self.assertIs(retrieved.metadata["provenance"]["nested"][2][0], True)
        self.assertIsNone(retrieved.metadata["provenance"]["nested"][2][2])
        self.assertEqual(reopened.get_node(plain.id).metadata, {})

    def test_06_reopen_preserves_complete_nodes_directed_edges_and_retrieval(self):
        store = self.store("persistent")
        nodes = [
            store.add_node("first", metadata={"provenance": {"source": "one"}}, weight=0),
            store.add_node("second", metadata={"list": [1, 2]}, weight=2.5),
            store.add_node("third", weight=1),
        ]
        first, second, third = nodes
        edges = [
            store.add_edge(first.id, second.id, "supports", weight=0.125, count=3),
            store.add_edge(first.id, second.id, "mentions", weight=0, count=1),
            store.add_edge(second.id, third.id, "next", weight=4, count=8),
        ]
        self.assertTrue(all(isinstance(edge, Edge) for edge in edges))
        before = store.retrieve([first.id], max_depth=2)
        self.assertEqual(before.nodes, tuple(nodes))
        self.assertEqual(before.traversed_edges, 3)
        store.close()
        reopened = self.store("persistent")
        self.assertEqual(tuple(reopened.get_node(node.id) for node in nodes), tuple(nodes))
        for edge in edges:
            self.assertEqual(reopened.get_edge(edge.source, edge.target, edge.relation), edge)
            self.assertIsNone(reopened.get_edge(edge.target, edge.source, edge.relation))
        self.assertEqual(reopened.retrieve([first.id], max_depth=2), before)
        self.assertEqual(reopened.retrieve([third.id]).nodes, (third,))
        self.assertEqual(reopened.retrieve([second.id]).nodes, (second, third))


class ContractSafeguards(StoreCase):
    """Additional checks reported separately from the six acceptance methods."""

    def test_namespace_rejects_empty_values_and_cannot_be_rebound(self):
        store = self.store()
        self.assertEqual(store.namespace, "default")
        with self.assertRaises(AttributeError):
            store.namespace = "other"
        with self.assertRaises(AttributeError):
            del store.namespace
        self.assertEqual(store.namespace, "default")
        for invalid in (None, "", " ", "\t\n"):
            with self.subTest(namespace=invalid), self.assertRaises(ValueError):
                with MemoryStore(":memory:", namespace=invalid):
                    self.fail("empty namespace accepted")

    def test_bfs_order_depth_and_budget_are_observable(self):
        store = self.store()
        seed = store.add_node("seed")
        neighbors = sorted([store.add_node(str(i)) for i in range(3)], key=lambda node: node.id)
        # Deliberately insert in the reverse of the contractual lexical order.
        for neighbor in reversed(neighbors):
            store.add_edge(seed.id, neighbor.id, "z")
            store.add_edge(seed.id, neighbor.id, "a")
        full = store.retrieve([seed.id, seed.id], max_depth=1, traversal_budget=6)
        self.assertEqual(full.nodes, (seed, *neighbors))
        self.assertEqual(full.visited_count, 4)
        self.assertEqual(full.traversed_edges, 6)  # Visited targets still consume budget.
        self.assertFalse(full.budget_exhausted)  # Exact completion is not exhaustion.
        limited = store.retrieve([seed.id], max_depth=1, traversal_budget=2)
        self.assertEqual(limited.nodes, (seed, neighbors[0]))
        self.assertEqual(limited.traversed_edges, 2)
        self.assertTrue(limited.budget_exhausted)
        capped = store.retrieve([seed.id], top_k=1, max_depth=1, traversal_budget=6)
        self.assertEqual(capped.nodes, (seed,))
        self.assertEqual(capped.visited_count, 4)
        self.assertEqual(capped.traversed_edges, 6)
        self.assertFalse(capped.budget_exhausted)
        zero_budget = store.retrieve([seed.id], traversal_budget=0)
        self.assertEqual(zero_budget.nodes, (seed,))
        self.assertTrue(zero_budget.budget_exhausted)
        no_expansion = store.retrieve([seed.id], max_depth=0, traversal_budget=0)
        self.assertEqual(no_expansion.nodes, (seed,))
        self.assertFalse(no_expansion.budget_exhausted)
        empty = store.retrieve([], traversal_budget=0)
        self.assertEqual(empty.nodes, ())
        self.assertFalse(empty.budget_exhausted)

    def test_runtime_source_imports_only_stdlib_and_this_package(self):
        package = Path(__file__).resolve().parents[1] / "src" / "tapestry_memory"
        sources = sorted(package.rglob("*.py"))
        self.assertTrue(sources, "must inspect actual package sources")
        allowed = set(sys.stdlib_module_names) | {"__future__", "tapestry_memory"}
        for source in sources:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    imports = [node.module or ""]
                else:
                    continue
                for imported in imports:
                    with self.subTest(file=source.name, line=node.lineno, imported=imported):
                        self.assertIn(imported.split(".")[0], allowed)

    def test_isolated_offline_import_has_no_filesystem_write_side_effects(self):
        src = Path(__file__).resolve().parents[1] / "src"
        script = textwrap.dedent(r'''
            import os
            import sys
            sys.dont_write_bytecode = True
            sys.path.insert(0, sys.argv[1])
            importing = True
            def audit(event, args):
                if event.startswith("socket."):
                    raise AssertionError("network forbidden: " + event)
                if importing and event == "sqlite3.connect":
                    raise AssertionError("database connection during import")
                if event == "open":
                    mode, flags = args[1], args[2]
                    if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                        isinstance(flags, int) and flags & (
                            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
                        )
                    ):
                        raise AssertionError("filesystem write forbidden: " + str(args[0]))
                if event in {
                    "os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link",
                    "os.symlink", "os.truncate", "os.chmod", "os.chown", "os.utime",
                    "os.system", "subprocess.Popen", "os.exec", "os.posix_spawn",
                }:
                    raise AssertionError("side effect forbidden: " + event)
            sys.addaudithook(audit)
            from tapestry_memory import MemoryStore, Node, Edge, RetrievalResult
            importing = False
            with MemoryStore() as store:
                first = store.add_node("offline", metadata={"provenance": "https://example.invalid"})
                second = store.add_node("local")
                store.add_edge(first.id, second.id, "next")
                assert store.retrieve([first.id]).nodes == (first, second)
            assert "site" not in sys.modules
            print("isolated offline import and in-memory operation passed")
        ''')
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-c", script, str(src)],
            cwd=self.directory.name,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("isolated offline import and in-memory operation passed", completed.stdout)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
