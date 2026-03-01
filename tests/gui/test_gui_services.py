import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from core.preset import Preset, Variable, VariableValue
from gui.services import move_images, rename_images, search_images


class GuiServicesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        (self.base / "a.png").write_bytes(b"")
        (self.base / "b.png").write_bytes(b"")

        self.preset = Preset(
            name="test",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                )
            ],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("gui.services.extract_tags_from_image", return_value=["tag1"])
    def test_rename_dry_run(self, _mock_extract) -> None:
        results = rename_images(
            self.preset,
            str(self.base),
            ["character"],
            template="[character]",
            dry_run=True,
        )
        ok = [item for item in results if item.get("status") == "OK"]
        self.assertEqual(len(ok), 2)
        self.assertTrue(any(Path(item["target"]).name.startswith("alice") for item in ok))
        self.assertTrue((self.base / "a.png").exists())

    @patch(
        "gui.services.extract_tags_from_image",
        side_effect=lambda path, include_negative: ["tag1"] if path.endswith("a.png") else ["tag2"],
    )
    def test_rename_unknown_contains_reason_message(self, _mock_extract) -> None:
        results = rename_images(
            self.preset,
            str(self.base),
            ["character"],
            template="[character]",
            dry_run=True,
        )
        unknown = [item for item in results if item.get("status") == "UNKNOWN"]
        self.assertEqual(len(unknown), 1)
        self.assertTrue(bool(unknown[0].get("message")))

    @patch("gui.services.extract_tags_from_image", return_value=["tag1"])
    def test_move_dry_run(self, _mock_extract) -> None:
        target = self.base / "out"
        results = move_images(
            self.preset,
            str(self.base),
            str(target),
            "character",
            dry_run=True,
        )
        ok = [item for item in results if item.get("status") == "OK"]
        self.assertEqual(len(ok), 2)
        self.assertTrue(all("alice" in item["target"] for item in ok))
        self.assertFalse(target.exists())

    @patch("gui.services.extract_tags_from_image", return_value=["tag1", "tag2"])
    def test_move_dry_run_nested_template(self, _mock_extract) -> None:
        target = self.base / "out"
        preset = Preset(
            name="test-nested",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                ),
                Variable(
                    name="emotion",
                    values=[VariableValue(name="happy", tags=["tag2"])],
                ),
            ],
        )
        results = move_images(
            preset,
            str(self.base),
            str(target),
            "character,emotion",
            folder_template="[character]/[emotion]",
            dry_run=True,
        )
        ok = [item for item in results if item.get("status") == "OK"]
        self.assertEqual(len(ok), 2)
        self.assertTrue(all("alice\\happy" in item["target"] or "alice/happy" in item["target"] for item in ok))

    @patch("gui.services.extract_tags_from_image", return_value=["tag1"])
    def test_move_dry_run_partial_prefix_match(self, _mock_extract) -> None:
        target = self.base / "out"
        preset = Preset(
            name="test-partial-prefix",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                ),
                Variable(
                    name="emotion",
                    values=[VariableValue(name="happy", tags=["tag2"])],
                ),
            ],
        )
        results = move_images(
            preset,
            str(self.base),
            str(target),
            "character,emotion",
            folder_template="[character]/[emotion]",
            dry_run=True,
        )
        ok = [item for item in results if item.get("status") == "OK"]
        self.assertEqual(len(ok), 2)
        self.assertTrue(all("alice" in item["target"] for item in ok))
        self.assertTrue(all("happy" not in item["target"] for item in ok))

    @patch("gui.services.extract_tags_from_image", return_value=["tag2"])
    def test_move_dry_run_upper_miss_lower_match_not_moved(self, _mock_extract) -> None:
        target = self.base / "out"
        preset = Preset(
            name="test-upper-miss",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                ),
                Variable(
                    name="emotion",
                    values=[VariableValue(name="happy", tags=["tag2"])],
                ),
            ],
        )
        results = move_images(
            preset,
            str(self.base),
            str(target),
            "character,emotion",
            folder_template="[character]/[emotion]",
            dry_run=True,
        )
        unknown = [item for item in results if item.get("status") == "UNKNOWN"]
        self.assertEqual(len(unknown), 2)
        self.assertTrue(all(item.get("target") is None for item in unknown))

    @patch(
        "gui.services.extract_tags_from_image",
        side_effect=lambda path, include_negative: ["tag1"] if path.endswith("a.png") else ["tag2"],
    )
    def test_search_images(self, _mock_extract) -> None:
        results = search_images(str(self.base), "tag1")
        ok = [item for item in results if item.get("status") == "OK"]
        self.assertEqual(len(ok), 1)
        self.assertTrue(ok[0]["source"].endswith("a.png"))


if __name__ == "__main__":
    unittest.main()
