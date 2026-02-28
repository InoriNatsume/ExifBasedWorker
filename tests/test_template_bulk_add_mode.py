from tests import _bootstrap  # noqa: F401

import unittest

from gui.template_editor.bulk import apply_value_name_add_mode


class TemplateBulkAddModeTests(unittest.TestCase):
    def test_apply_value_name_add_mode_suffix(self) -> None:
        self.assertEqual(
            apply_value_name_add_mode("alice", "_happy", "뒤에 추가"),
            "alice_happy",
        )

    def test_apply_value_name_add_mode_prefix(self) -> None:
        self.assertEqual(
            apply_value_name_add_mode("alice", "char_", "앞에 추가"),
            "char_alice",
        )

    def test_apply_value_name_add_mode_unknown_defaults_to_suffix(self) -> None:
        self.assertEqual(
            apply_value_name_add_mode("alice", "_v2", "알수없음"),
            "alice_v2",
        )


if __name__ == "__main__":
    unittest.main()
