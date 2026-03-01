import json
import unittest

from core.extract import unwrap_comment_payload


class ExtractTests(unittest.TestCase):
    def test_unwrap_comment_dict(self) -> None:
        payload = {"Comment": {"prompt": "1girl"}}
        result = unwrap_comment_payload(payload)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].get("prompt"), "1girl")

    def test_unwrap_comment_json_string(self) -> None:
        payload = {"Comment": json.dumps({"prompt": "1girl"})}
        result = unwrap_comment_payload(payload)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].get("prompt"), "1girl")


if __name__ == "__main__":
    unittest.main()
