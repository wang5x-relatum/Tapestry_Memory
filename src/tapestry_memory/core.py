"""Namespace-bound, offline graph storage and bounded outgoing BFS."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator
from uuid import uuid4


@dataclass(frozen=True)
class Node:
    id: str
    content: str
    metadata: dict[str, Any]
    created_at: str
    weight: float


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str
    weight: float
    count: int
    created_at: str


@dataclass(frozen=True)
class RetrievalResult:
    nodes: tuple[Node, ...]
    visited_count: int
    traversed_edges: int
    budget_exhausted: bool


_UNSET = object()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value


def _weight(value: Any) -> float:
    if type(value) not in (int, float):
        raise ValueError("weight must be a finite nonnegative number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("weight must be finite") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError("weight must be a finite nonnegative number")
    return number


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _metadata(value: Any) -> str:
    if value is None:
        value = {}
    if type(value) is not dict:
        raise ValueError("metadata must be a JSON object")
    active: set[int] = set()

    def check(item: Any) -> None:
        kind = type(item)
        if item is None or kind in (str, bool, int):
            return
        if kind is float and math.isfinite(item):
            return
        if kind not in (dict, list):
            raise ValueError("metadata must contain only native, finite JSON values")
        identity = id(item)
        if identity in active:
            raise ValueError("metadata must not contain cycles")
        active.add(identity)
        if kind is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError("metadata object keys must be strings")
                check(child)
        else:
            for child in item:
                check(child)
        active.remove(identity)

    try:
        check(value)
        return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    except (RecursionError, OverflowError) as exc:
        raise ValueError("metadata exceeds JSON nesting or numeric limits") from exc


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    namespace TEXT NOT NULL,
    id TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    weight REAL NOT NULL CHECK(weight >= 0),
    deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0, 1)),
    PRIMARY KEY(namespace, id)
);
CREATE TABLE IF NOT EXISTS edges (
    namespace TEXT NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL NOT NULL CHECK(weight >= 0),
    count INTEGER NOT NULL CHECK(count > 0),
    created_at TEXT NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0, 1)),
    PRIMARY KEY(namespace, source, target, relation),
    FOREIGN KEY(namespace, source) REFERENCES nodes(namespace, id),
    FOREIGN KEY(namespace, target) REFERENCES nodes(namespace, id)
);
CREATE INDEX IF NOT EXISTS edges_outgoing_live
    ON edges(namespace, source, target, relation) WHERE deleted = 0;
CREATE INDEX IF NOT EXISTS edges_incoming_live
    ON edges(namespace, target) WHERE deleted = 0;
"""


class MemoryStore:
    """One SQLite connection bound to one namespace; not a host security boundary.

    Each successful write commits unless enclosed in ``transaction()``. Returned
    records are detached snapshots, including their nested metadata. Instances
    follow SQLite's default same-thread rule; use another instance per thread.
    """

    def __init__(self, path: str | Path = ":memory:", *, namespace: str = "default"):
        self._namespace = _text(namespace, "namespace")
        self._connection = sqlite3.connect(path, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._savepoint = 0
        self._depth = 0
        self._closed = False
        try:
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Claim only an empty database. Never adopt or overwrite an unrelated
            # application's tables, even if their names happen to match ours.
            with self.transaction():
                application_id = self._connection.execute("PRAGMA application_id").fetchone()[0]
                version = self._connection.execute("PRAGMA user_version").fetchone()[0]
                tables = self._connection.execute(
                    "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if application_id == 0 and version == 0 and not tables:
                    for statement in _SCHEMA.split(";"):
                        if statement.strip():
                            self._connection.execute(statement)
                    self._connection.execute("PRAGMA application_id = 1413566547")
                    self._connection.execute("PRAGMA user_version = 1")
                elif application_id != 1413566547 or version != 1:
                    raise ValueError("database is not a supported tapestry-memory database")
        except BaseException:
            self._connection.close()
            raise

    @property
    def namespace(self) -> str:
        return self._namespace

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("MemoryStore is closed")

    def close(self) -> None:
        """Close idempotently; an active transaction must exit before closing."""
        if self._depth:
            raise RuntimeError("cannot close inside an active transaction")
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> MemoryStore:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[MemoryStore]:
        """Commit on success; rollback this block only on any exception.

        Every nested block uses a savepoint, including individual writes. A
        caller may catch an inner failure and still commit the outer block.
        """
        self._ensure_open()
        outer = self._depth == 0
        self._savepoint += 1
        name = f"tapestry_{self._savepoint}"
        self._connection.execute("BEGIN" if outer else f"SAVEPOINT {name}")
        self._depth += 1
        try:
            yield self
            self._connection.execute("COMMIT" if outer else f"RELEASE {name}")
        except BaseException:
            if outer:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
            else:
                self._connection.execute(f"ROLLBACK TO {name}")
                self._connection.execute(f"RELEASE {name}")
            raise
        finally:
            self._depth -= 1

    @staticmethod
    def _node(row: sqlite3.Row) -> Node:
        return Node(row["id"], row["content"], json.loads(row["metadata"]),
                    row["created_at"], row["weight"])

    @staticmethod
    def _edge(row: sqlite3.Row) -> Edge:
        return Edge(row["source"], row["target"], row["relation"],
                    row["weight"], row["count"], row["created_at"])

    def add_node(self, content: str, *, metadata: dict[str, Any] | None = None,
                 weight: float = 1.0) -> Node:
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        encoded, number = _metadata(metadata), _weight(weight)
        node_id, created = str(uuid4()), _now()
        with self.transaction():
            self._connection.execute(
                "INSERT INTO nodes(namespace,id,content,metadata,created_at,weight) "
                "VALUES(?,?,?,?,?,?)",
                (self.namespace, node_id, content, encoded, created, number),
            )
        return Node(node_id, content, json.loads(encoded), created, number)

    def get_node(self, node_id: str) -> Node | None:
        self._ensure_open()
        _text(node_id, "node_id")
        row = self._connection.execute(
            "SELECT * FROM nodes WHERE namespace=? AND id=? AND deleted=0",
            (self.namespace, node_id),
        ).fetchone()
        return self._node(row) if row is not None else None

    def update_node(self, node_id: str, *, content: Any = _UNSET,
                    metadata: Any = _UNSET, weight: Any = _UNSET) -> Node:
        _text(node_id, "node_id")
        if content is not _UNSET and not isinstance(content, str):
            raise ValueError("content must be a string")
        encoded = _metadata(metadata) if metadata is not _UNSET else _UNSET
        number = _weight(weight) if weight is not _UNSET else _UNSET
        with self.transaction():
            previous = self.get_node(node_id)
            if previous is None:
                raise KeyError(node_id)
            new_content = previous.content if content is _UNSET else content
            new_metadata = _metadata(previous.metadata) if encoded is _UNSET else encoded
            new_weight = previous.weight if number is _UNSET else number
            self._connection.execute(
                "UPDATE nodes SET content=?,metadata=?,weight=? WHERE namespace=? AND id=? AND deleted=0",
                (new_content, new_metadata, new_weight, self.namespace, node_id),
            )
            return Node(node_id, new_content, json.loads(new_metadata), previous.created_at, new_weight)

    def add_edge(self, source: str, target: str, relation: str, *,
                 weight: float = 1.0, count: int = 1) -> Edge:
        _text(source, "source")
        _text(target, "target")
        _text(relation, "relation")
        number = _weight(weight)
        _integer(count, "count", 1)
        if count > 2**63 - 1:
            raise ValueError("count exceeds SQLite's signed 64-bit integer range")
        with self.transaction():
            if self.get_node(source) is None:
                raise KeyError(source)
            if self.get_node(target) is None:
                raise KeyError(target)
            # Re-adding a deleted edge is an explicit resurrection. Its original
            # creation time survives, as it does on a live edge replacement.
            self._connection.execute(
                "INSERT INTO edges(namespace,source,target,relation,weight,count,created_at) "
                "VALUES(?,?,?,?,?,?,?) ON CONFLICT(namespace,source,target,relation) "
                "DO UPDATE SET weight=excluded.weight,count=excluded.count,deleted=0",
                (self.namespace, source, target, relation, number, count, _now()),
            )
            result = self.get_edge(source, target, relation)
            assert result is not None
            return result

    def get_edge(self, source: str, target: str, relation: str) -> Edge | None:
        self._ensure_open()
        for name, value in (("source", source), ("target", target), ("relation", relation)):
            _text(value, name)
        row = self._connection.execute(
            "SELECT * FROM edges WHERE namespace=? AND source=? AND target=? AND relation=? AND deleted=0",
            (self.namespace, source, target, relation),
        ).fetchone()
        return self._edge(row) if row is not None else None

    def delete_edge(self, source: str, target: str, relation: str) -> bool:
        for name, value in (("source", source), ("target", target), ("relation", relation)):
            _text(value, name)
        with self.transaction():
            cursor = self._connection.execute(
                "UPDATE edges SET deleted=1 WHERE namespace=? AND source=? AND target=? AND relation=? AND deleted=0",
                (self.namespace, source, target, relation),
            )
            return cursor.rowcount > 0

    def delete_node(self, node_id: str) -> bool:
        """Hide a local node and all incident edges; not physical erasure.

        No derived records or caches are maintained. Backups, source documents,
        and forensic recovery from SQLite files are outside this guarantee.
        """
        _text(node_id, "node_id")
        with self.transaction():
            cursor = self._connection.execute(
                "UPDATE nodes SET deleted=1 WHERE namespace=? AND id=? AND deleted=0",
                (self.namespace, node_id),
            )
            if not cursor.rowcount:
                return False
            # Separate indexed updates avoid scanning unrelated edges for OR.
            for endpoint in ("source", "target"):
                self._connection.execute(
                    f"UPDATE edges SET deleted=1 WHERE namespace=? AND {endpoint}=? AND deleted=0",
                    (self.namespace, node_id),
                )
            return True

    def retrieve(self, seed_ids: Iterable[str], *, top_k: int = 10,
                 max_depth: int = 2, traversal_budget: int = 1000) -> RetrievalResult:
        """Return outgoing BFS discovery order, not semantic or weight ranking.

        Seeds preserve caller order and count as depth zero. Neighbors sort by
        target ID then relation. Every examined edge costs one unit, even when
        its target is already visited. top_k caps output, not traversal work.
        A bounded one-row lookahead detects exhaustion without materializing or
        sorting a high-degree adjacency list (the live index supplies order).
        Seed ingestion costs O(number of supplied seeds), outside edge budget.
        """
        _integer(top_k, "top_k")
        _integer(max_depth, "max_depth")
        _integer(traversal_budget, "traversal_budget")
        if isinstance(seed_ids, (str, bytes)):
            raise ValueError("seed_ids must be an iterable of node IDs, not a string")
        try:
            seeds = iter(seed_ids)
        except TypeError as exc:
            raise ValueError("seed_ids must be an iterable of node IDs") from exc
        seen: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        output: list[Node] = []
        traversed = 0
        # A read transaction keeps seeds, expansions and outputs in one snapshot.
        with self.transaction():
            for seed in seeds:
                _text(seed, "seed ID")
                if seed in seen:
                    continue
                node = self.get_node(seed)
                if node is not None:
                    seen.add(seed)
                    queue.append((seed, 0))
                    if len(output) < top_k:
                        output.append(node)
            while queue:
                source, depth = queue.popleft()
                if depth >= max_depth:
                    continue
                remaining = traversal_budget - traversed
                # LIMIT caps rows read, not merely rows ultimately returned.
                # The extra row is only an exhaustion probe, not an expansion.
                limit = min(remaining + 1, 2**63 - 1)
                cursor = self._connection.execute(
                    "SELECT target FROM edges WHERE namespace=? AND source=? AND deleted=0 "
                    "ORDER BY target,relation LIMIT ?",
                    (self.namespace, source, limit),
                )
                try:
                    for row in cursor:
                        if traversed == traversal_budget:
                            return RetrievalResult(tuple(output), len(seen), traversed, True)
                        traversed += 1
                        target = row["target"]
                        if target in seen:
                            continue
                        node = self.get_node(target)
                        if node is None:
                            continue
                        seen.add(target)
                        queue.append((target, depth + 1))
                        if len(output) < top_k:
                            output.append(node)
                finally:
                    cursor.close()
        return RetrievalResult(tuple(output), len(seen), traversed, False)
