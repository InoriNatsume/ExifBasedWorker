from tests import _bootstrap  # noqa: F401

import unittest

from core.preset import Preset, Variable, VariableValue
from gui.template_editor.ops import (
    add_value,
    add_variable,
    delete_value,
    delete_variable,
    rename_variable,
    update_value,
)


class TemplateOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preset = Preset(
            name="template",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                )
            ],
        )

    def test_add_and_delete_variable(self) -> None:
        updated = add_variable(self.preset, "emotion")
        self.assertEqual(len(updated.variables), 2)
        updated = delete_variable(updated, 1)
        self.assertEqual(len(updated.variables), 1)

    def test_rename_variable(self) -> None:
        updated = rename_variable(self.preset, 0, "char")
        self.assertEqual(updated.variables[0].name, "char")

    def test_add_update_delete_value(self) -> None:
        updated = add_value(self.preset, 0, "bob", ["tag2", "tag3"])
        self.assertEqual(len(updated.variables[0].values), 2)
        updated = update_value(updated, 0, 1, "bob2", ["tag2"])
        self.assertEqual(updated.variables[0].values[1].name, "bob2")
        updated = delete_value(updated, 0, 1)
        self.assertEqual(len(updated.variables[0].values), 1)


if __name__ == "__main__":
    unittest.main()
