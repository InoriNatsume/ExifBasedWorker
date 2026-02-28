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
    def __init__(self, preset: Preset, template_path: str | None = None) -> None:
        self.state = AppState(preset=preset, template_path=template_path)
        self.template_status_var = _StatusVar()
        self.template_editor = None
        self.refreshed = False

    def _refresh_template_ui(self) -> None:
        self.refreshed = True


class TemplateLoadModesTests(unittest.TestCase):
    def test_load_template_reset_replaces_current_preset(self) -> None:
        app = _DummyTemplateApp(
            Preset(
                name="current",
                variables=[Variable(name="a", values=[VariableValue(name="v1", tags=["t1"])])],
            ),
            template_path="C:/old/current.json",
        )
        incoming = Preset(
            name="incoming",
            variables=[Variable(name="b", values=[VariableValue(name="v2", tags=["t2"])])],
        )

        with (
            patch("gui.app.template_mixin.filedialog.askopenfilename", return_value="C:/new/incoming.json"),
            patch("gui.app.template_mixin.load_preset", return_value=incoming),
        ):
            app._load_template_reset()

        self.assertEqual(len(app.state.preset.variables), 1)
        self.assertEqual(app.state.preset.variables[0].name, "b")
        self.assertEqual(app.state.template_path, "C:/new/incoming.json")
        self.assertTrue(app.refreshed)
        self.assertIn("불러오기 완료", app.template_status_var.value)

    def test_load_template_add_variables_appends_when_no_conflict(self) -> None:
        app = _DummyTemplateApp(
            Preset(
                name="current",
                variables=[Variable(name="a", values=[VariableValue(name="v1", tags=["t1"])])],
            ),
            template_path="C:/old/current.json",
        )
        incoming = Preset(
            name="incoming",
            variables=[Variable(name="b", values=[VariableValue(name="v2", tags=["t2"])])],
        )

        with (
            patch("gui.app.template_mixin.filedialog.askopenfilename", return_value="C:/new/incoming.json"),
            patch("gui.app.template_mixin.load_preset", return_value=incoming),
            patch("gui.app.template_mixin.messagebox.showwarning") as mock_warning,
        ):
            app._load_template_add_variables()

        self.assertEqual(len(app.state.preset.variables), 2)
        self.assertEqual(app.state.preset.variables[0].name, "a")
        self.assertEqual(app.state.preset.variables[1].name, "b")
        self.assertEqual(app.state.template_path, "C:/old/current.json")
        self.assertTrue(app.refreshed)
        self.assertIn("변수 추가 불러오기 완료", app.template_status_var.value)
        mock_warning.assert_not_called()

    def test_load_template_add_variables_conflict_does_nothing(self) -> None:
        app = _DummyTemplateApp(
            Preset(
                name="current",
                variables=[Variable(name="a", values=[VariableValue(name="v1", tags=["t1"])])],
            ),
            template_path="C:/old/current.json",
        )
        incoming = Preset(
            name="incoming",
            variables=[Variable(name="a", values=[VariableValue(name="v2", tags=["t2"])])],
        )

        with (
            patch("gui.app.template_mixin.filedialog.askopenfilename", return_value="C:/new/incoming.json"),
            patch("gui.app.template_mixin.load_preset", return_value=incoming),
            patch("gui.app.template_mixin.messagebox.showwarning") as mock_warning,
        ):
            app._load_template_add_variables()

        self.assertEqual(len(app.state.preset.variables), 1)
        self.assertEqual(app.state.preset.variables[0].name, "a")
        self.assertEqual(app.state.preset.variables[0].values[0].name, "v1")
        self.assertEqual(app.state.template_path, "C:/old/current.json")
        self.assertFalse(app.refreshed)
        self.assertIn("변수 충돌", app.template_status_var.value)
        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
