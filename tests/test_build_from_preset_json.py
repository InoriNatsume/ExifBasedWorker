from tests import _bootstrap  # noqa: F401

import json
import tempfile
from pathlib import Path
import unittest

from gui.services import build_variable_from_preset_json


class BuildFromPresetJsonTests(unittest.TestCase):
    def test_build_variable_from_preset_json(self) -> None:
        payload = {
            "name": "Emotion Preset",
            "scenes": [
                {"name": "happy", "scenePrompt": "smile, open mouth"},
                {"name": "sad", "scenePrompt": "tears, frown"},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "preset.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            variable, stats = build_variable_from_preset_json(str(json_path))
            self.assertEqual(variable.name, "Emotion Preset")
            self.assertEqual(len(variable.values), 2)
            self.assertEqual(stats.get("total_values"), 2)
            self.assertEqual(stats.get("imported_values"), 2)
            self.assertEqual(stats.get("removed_empty"), 0)

    def test_build_variable_from_preset_json_filters_empty_tags(self) -> None:
        payload = {
            "name": "Has Empty",
            "scenes": [
                {"name": "empty", "scenePrompt": ""},
                {"name": "ok", "scenePrompt": "tag1"},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "preset.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            variable, stats = build_variable_from_preset_json(str(json_path))
            self.assertEqual(len(variable.values), 1)
            self.assertEqual(variable.values[0].name, "ok")
            self.assertEqual(stats.get("removed_empty"), 1)


if __name__ == "__main__":
    unittest.main()
