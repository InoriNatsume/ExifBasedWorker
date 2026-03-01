import unittest
from unittest.mock import patch

from gui.services import build_variable_from_folder


class BuildFromFolderTests(unittest.TestCase):
    @patch("gui.services_ops.build_ops.build_nais_from_folder")
    def test_build_variable_from_folder(self, mock_builder) -> None:
        mock_builder.return_value = (
            {
                "name": "sample_folder",
                "scenes": [
                    {"name": "alice_happy", "scenePrompt": "alice, happy"},
                ],
            },
            {"total": 1, "common_count": 0, "empty_unique": 0},
        )

        variable, stats = build_variable_from_folder("C:/dummy")

        self.assertEqual(variable.name, "sample_folder")
        self.assertEqual(len(variable.values), 1)
        self.assertEqual(variable.values[0].name, "alice_happy")
        self.assertIn("alice", variable.values[0].tags)
        self.assertEqual(stats.get("total"), 1)
        self.assertEqual(stats.get("removed_conflicts"), 0)


if __name__ == "__main__":
    unittest.main()
