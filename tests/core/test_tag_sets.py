import unittest

from core.preset import VariableValue
from core.match import detect_value_conflicts
from core.utils import compute_common_tags, remove_common_tags_from_values


class TagSetTests(unittest.TestCase):
    def test_compute_common_tags_order(self) -> None:
        tags = [
            ["a", "b", "c"],
            ["c", "b", "a", "d"],
            ["b", "a"],
        ]
        common = compute_common_tags(tags)
        self.assertEqual(common, ["a", "b"])

    def test_remove_common_tags_from_values(self) -> None:
        values = [
            VariableValue(name="v1", tags=["a", "b", "x"]),
            VariableValue(name="v2", tags=["b", "a", "y"]),
            VariableValue(name="v3", tags=["a", "b", "z"]),
        ]
        updated, common = remove_common_tags_from_values(values)
        self.assertEqual(common, ["a", "b"])
        self.assertEqual(updated[0].tags, ["x"])
        self.assertEqual(updated[1].tags, ["y"])
        self.assertEqual(updated[2].tags, ["z"])

    def test_remove_common_tags_no_common(self) -> None:
        values = [
            VariableValue(name="v1", tags=["a"]),
            VariableValue(name="v2", tags=["b"]),
        ]
        updated, common = remove_common_tags_from_values(values)
        self.assertEqual(common, [])
        self.assertEqual(updated[0].tags, ["a"])
        self.assertEqual(updated[1].tags, ["b"])

    def test_remove_common_tags_single_value(self) -> None:
        values = [VariableValue(name="v1", tags=["a", "b"])]
        updated, common = remove_common_tags_from_values(values)
        self.assertEqual(common, ["a", "b"])
        self.assertEqual(updated[0].tags, [])

    def test_remove_common_tags_empty_tags(self) -> None:
        values = [
            VariableValue(name="v1", tags=[]),
            VariableValue(name="v2", tags=[]),
        ]
        updated, common = remove_common_tags_from_values(values)
        self.assertEqual(common, [])
        self.assertEqual(updated[0].tags, [])
        self.assertEqual(updated[1].tags, [])

    def test_conflict_detection_duplicate(self) -> None:
        values = [
            VariableValue(name="v1", tags=["a", "b"]),
            VariableValue(name="v2", tags=["a", "b"]),
        ]
        summary = detect_value_conflicts(values)
        self.assertTrue(summary.has_conflicts)
        self.assertEqual(len(summary.duplicate_pairs), 1)
        self.assertEqual(len(summary.subset_pairs), 0)

    def test_conflict_detection_subset(self) -> None:
        values = [
            VariableValue(name="v1", tags=["a"]),
            VariableValue(name="v2", tags=["a", "b"]),
        ]
        summary = detect_value_conflicts(values)
        self.assertTrue(summary.has_conflicts)
        self.assertEqual(len(summary.subset_pairs), 1)


if __name__ == "__main__":
    unittest.main()
