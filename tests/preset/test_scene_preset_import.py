import unittest

from core.adapters.scene_preset import import_scene_preset_payload


class ScenePresetImportTests(unittest.TestCase):
    def test_import_standard_scenes_array(self) -> None:
        payload = {
            "name": "NAIS2 Pack",
            "scenes": [
                {"name": "happy", "scenePrompt": "smile, open mouth"},
                {"scene_name": "sad", "scene_prompt": "tears, frown"},
            ],
        }
        name, values = import_scene_preset_payload(payload)
        self.assertEqual(name, "NAIS2 Pack")
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0].name, "happy")
        self.assertIn("smile", values[0].tags)

    def test_import_legacy_array_format(self) -> None:
        payload = [
            {"scene_name": "angry", "scene_prompt": "frown, clenched hand"},
        ]
        name, values = import_scene_preset_payload(payload)
        self.assertIsNone(name)
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].name, "angry")
        self.assertIn("frown", values[0].tags)

    def test_import_scenes_object_slots_enabled_default_true(self) -> None:
        payload = {
            "name": "Interaction Share",
            "scenes": {
                "1": {
                    "name": "pose",
                    "slots": [
                        [{"prompt": "A"}, {"prompt": "B", "enabled": False}],
                        [{"prompt": "C"}],
                    ],
                }
            },
        }
        _name, values = import_scene_preset_payload(payload)
        self.assertEqual(len(values), 1)
        # enabled 누락 항목(A)은 활성으로 처리, B는 비활성 처리되어야 한다.
        self.assertEqual(values[0].name, "pose")
        self.assertIn("A", values[0].tags)
        self.assertNotIn("B", values[0].tags)
        self.assertIn("C", values[0].tags)

    def test_import_sdstudio_presets(self) -> None:
        payload = {
            "name": "SD Pack",
            "presets": {
                "SDImageGenEasy": [
                    {"name": "v1", "frontPrompt": "girl", "backPrompt": "smile"},
                    {"name": "v2", "frontPrompt": "boy"},
                ]
            },
        }
        name, values = import_scene_preset_payload(payload)
        self.assertEqual(name, "SD Pack")
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0].name, "v1")
        self.assertIn("girl", values[0].tags)
        self.assertIn("smile", values[0].tags)

    def test_import_unknown_format_raises(self) -> None:
        with self.assertRaises(ValueError):
            import_scene_preset_payload({"hello": "world"})


if __name__ == "__main__":
    unittest.main()
