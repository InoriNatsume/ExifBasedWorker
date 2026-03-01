import unittest

from core.normalize import merge_prompt_tags, normalize_novelai_payload, split_novelai_tags


class NormalizeTests(unittest.TestCase):
    def test_split_tags_basic(self) -> None:
        text = "1::tag a::, {tag b}, [tag c], ||tag d||, tag e|tag f"
        tags = split_novelai_tags(text)
        self.assertIn("tag a", tags)
        self.assertIn("tag b", tags)
        self.assertIn("tag c", tags)
        self.assertIn("tag d", tags)
        self.assertIn("tag e", tags)
        self.assertIn("tag f", tags)

    def test_merge_prompt_tags(self) -> None:
        payload = {
            "prompt": "tag1, tag2",
            "v4_prompt": {
                "caption": {
                    "char_captions": [
                        {"char_caption": "tag3, tag4"},
                    ]
                }
            },
        }
        normalized = normalize_novelai_payload(payload)
        tags = merge_prompt_tags(normalized, include_negative=False)
        self.assertIn("tag1", tags)
        self.assertIn("tag4", tags)


if __name__ == "__main__":
    unittest.main()
