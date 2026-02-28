from tests import _bootstrap  # noqa: F401

import unittest
from unittest.mock import patch

from core.preset import Preset, Variable, VariableValue
from gui.app.template_mixin import TemplateWorkflowMixin
from gui.state import AppState


class _StatusVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _DummyTemplateApp(TemplateWorkflowMixin):
    def __init__(self, preset: Preset) -> None:
        self.state = AppState(preset=preset, template_path=None)
        self.template_status_var = _StatusVar()
        self.refreshed = False

    def _refresh_template_ui(self) -> None:
        self.refreshed = True


class TemplateGenerationApplyTests(unittest.TestCase):
    def test_apply_generated_variable_conflict_keeps_preset_unchanged(self) -> None:
        preset = Preset(
            name="sample",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                )
            ],
        )
        app = _DummyTemplateApp(preset)
        incoming = Variable(
            name="character",
            values=[VariableValue(name="bob", tags=["tag2"])],
        )

        with patch("gui.app.template_mixin.messagebox.showwarning") as mock_warning:
            app._apply_generated_variable(incoming, {}, status_prefix="생성 완료")

        self.assertEqual(len(app.state.preset.variables), 1)
        self.assertEqual(app.state.preset.variables[0].name, "character")
        self.assertEqual(app.state.preset.variables[0].values[0].name, "alice")
        self.assertFalse(app.refreshed)
        self.assertIn("변수 충돌", app.template_status_var.value)
        self.assertIn("동일한 변수 이름", app.template_status_var.value)
        mock_warning.assert_called_once()

    def test_apply_generated_variable_adds_when_no_conflict(self) -> None:
        preset = Preset(
            name="sample",
            variables=[
                Variable(
                    name="character",
                    values=[VariableValue(name="alice", tags=["tag1"])],
                )
            ],
        )
        app = _DummyTemplateApp(preset)
        incoming = Variable(
            name="emotion",
            values=[VariableValue(name="happy", tags=["tag2"])],
        )

        with patch("gui.app.template_mixin.messagebox.showwarning") as mock_warning:
            app._apply_generated_variable(incoming, {}, status_prefix="생성 완료")

        self.assertEqual(len(app.state.preset.variables), 2)
        self.assertEqual(app.state.preset.variables[1].name, "emotion")
        self.assertTrue(app.refreshed)
        self.assertEqual(app.template_status_var.value, "생성 완료")
        mock_warning.assert_not_called()


if __name__ == "__main__":
    unittest.main()
