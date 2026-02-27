from __future__ import annotations

from pathlib import Path
import tkinter as tk

from core.preset import Preset
from core.preset.io import load_preset

from ..template_editor import validate_preset_for_ui


class TaskTemplateSelectionMixin:
    def _list_saved_template_files(self) -> list[Path]:
        templates_dir = Path("templates")
        templates_dir.mkdir(parents=True, exist_ok=True)
        return sorted(templates_dir.glob("*.json"))

    def _refresh_task_template_choices(self) -> None:
        files = self._list_saved_template_files()
        self.task_template_paths = {path.name: str(path.resolve()) for path in files}
        values = list(self.task_template_paths.keys())

        if self.rename_template_combo:
            self.rename_template_combo["values"] = values
        if self.move_template_combo:
            self.move_template_combo["values"] = values

        current_name = ""
        if self.state.template_path:
            candidate = Path(self.state.template_path).name
            if candidate in self.task_template_paths:
                current_name = candidate
        default_name = current_name or (values[0] if values else "")
        self._ensure_task_template_selection(self.rename_template_file_var, values, default_name)
        self._ensure_task_template_selection(self.move_template_file_var, values, default_name)

    @staticmethod
    def _ensure_task_template_selection(
        target_var: tk.StringVar,
        choices: list[str],
        default_choice: str,
    ) -> None:
        selected = target_var.get().strip()
        if selected in choices:
            return
        target_var.set(default_choice)

    def _resolve_task_preset(self, template_path_text: str) -> tuple[Preset, str]:
        if self.template_editor:
            self.template_editor.flush_pending_edits()

        selected_name = template_path_text.strip()
        if not selected_name:
            raise ValueError("templates 폴더에서 사용할 템플릿을 선택하세요.")

        selected_path = self.task_template_paths.get(selected_name)
        if not selected_path:
            self._refresh_task_template_choices()
            selected_path = self.task_template_paths.get(selected_name)
        if not selected_path:
            raise ValueError(f"templates 폴더에서 템플릿을 찾을 수 없습니다: {selected_name}")

        current = str(Path(self.state.template_path).resolve()) if self.state.template_path else ""
        if current and Path(selected_path).resolve() == Path(current).resolve():
            preset = self.state.preset
            validate_preset_for_ui(preset)
            return preset, selected_name

        preset = load_preset(selected_path)
        validate_preset_for_ui(preset)
        return preset, selected_name
