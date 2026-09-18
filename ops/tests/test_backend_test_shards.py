from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/run-backend-test-shard.py"


def load_module():
    spec = importlib.util.spec_from_file_location("backend_test_shard", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BackendTestShardTests(unittest.TestCase):
    def test_partitions_are_stable_disjoint_and_complete(self) -> None:
        module = load_module()
        nodeids = tuple(f"tests/test_example.py::test_{index}" for index in range(17))

        partitions = [module.partition_nodeids(nodeids, total=4, index=index) for index in range(4)]

        flattened = [nodeid for partition in partitions for nodeid in partition]
        self.assertEqual(sorted(flattened), sorted(nodeids))
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(partitions[2], module.partition_nodeids(nodeids, total=4, index=2))

    def test_partition_rejects_invalid_bounds(self) -> None:
        module = load_module()
        with self.assertRaises(ValueError):
            module.partition_nodeids(("tests/a.py::test_a",), total=0, index=0)
        with self.assertRaises(ValueError):
            module.partition_nodeids(("tests/a.py::test_a",), total=4, index=4)

    def test_time_varying_parameter_id_keeps_same_collection_position(self) -> None:
        module = load_module()
        first = ("tests/a.py::test_a", "tests/a.py::test_expires_at[100]")
        later = ("tests/a.py::test_a", "tests/a.py::test_expires_at[200]")

        self.assertEqual(module.partition_nodeids(first, total=4, index=1), (first[1],))
        self.assertEqual(module.partition_nodeids(later, total=4, index=1), (later[1],))

    def test_manifest_normalizes_time_varying_parameter_ids(self) -> None:
        module = load_module()
        first = ("tests/a.py::test_expires_at[100]",)
        later = ("tests/a.py::test_expires_at[200]",)

        self.assertEqual(module.collection_manifest(first), module.collection_manifest(later))

    def test_ci_runs_all_shards_in_fresh_processes(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("run-backend-test-shard.py", workflow)
        self.assertIn("for shard in 0 1 2 3", workflow)
        self.assertIn("--manifest", workflow)
        self.assertNotIn("- run: uv run pytest\n", workflow)


if __name__ == "__main__":
    unittest.main()
