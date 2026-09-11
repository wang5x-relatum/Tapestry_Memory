"""Run a complete offline tapestry-memory lifecycle with synthetic data."""

from pathlib import Path
from tempfile import TemporaryDirectory

from tapestry_memory import MemoryStore


def main() -> None:
    with TemporaryDirectory() as directory:
        database = Path(directory) / "example.sqlite3"

        with MemoryStore(database, namespace="demo") as store:
            observation = store.add_node(
                "The local sensor reported clear weather.",
                metadata={"provenance": {"source": "synthetic:weather-demo"}},
            )
            decision = store.add_node("Pack a light jacket.")
            store.add_edge(observation.id, decision.id, "supports", weight=0.8)

            result = store.retrieve([observation.id], max_depth=1)
            assert result.nodes == (observation, decision)
            assert store.get_node(decision.id) == decision

            assert store.delete_node(decision.id)
            assert store.get_node(decision.id) is None
            assert store.get_edge(observation.id, decision.id, "supports") is None

        with MemoryStore(database, namespace="demo") as reopened:
            assert reopened.get_node(observation.id) == observation
            assert reopened.get_node(decision.id) is None

        print("offline add, edge, retrieve, delete, and reopen passed")


if __name__ == "__main__":
    main()
