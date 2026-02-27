from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog, messagebox

from core.preset import Preset
from core.preset.io import load_preset, save_preset
from core.utils import sanitize_filename

from ..services import build_variable_from_folder, build_variable_from_preset_json
from ..template_editor import validate_preset_for_ui


class TemplateWorkflowMixin:
    def _refresh_template_ui(self) -> None:
        self.template_path_var.set(self.state.template_path or "")
        if self.template_editor:
            self.template_editor.refresh()

        if not self.rename_order_var.get().strip():
            self._fill_rename_order()

        if not self.move_order_var.get().strip():
            self._fill_move_order()
        self._refresh_task_template_choices()

    def _get_preset(self) -> Preset:
        return self.state.preset

    def _set_preset(self, preset: Preset) -> None:
        self.state.preset = preset

    def _load_template(self) -> None:
        path = filedialog.askopenfilename(
            title="템플릿 불러오기",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            preset = load_preset(path)
            self.state.set_preset(preset, path)
            self._refresh_template_ui()
            self.template_status_var.set(f"불러오기 완료: {path}")
            logging.info("템플릿 불러오기: %s", path)
        except Exception as exc:
            messagebox.showerror("템플릿", f"불러오기 실패: {exc}")

    def _save_template(self) -> None:
        if self.template_editor:
            self.template_editor.flush_pending_edits()

        current_path = self.state.template_path
        if current_path:
            current = Path(current_path)
            initial_dir = str(current.parent)
            initial_name = current.name
        else:
            templates_dir = Path("templates")
            templates_dir.mkdir(parents=True, exist_ok=True)
            initial_dir = str(templates_dir.resolve())
            base = sanitize_filename(self.state.get_template_name(), fallback="template")
            initial_name = f"{base}.json"

        path = filedialog.asksaveasfilename(
            title="템플릿 저장",
            defaultextension=".json",
            initialdir=initial_dir,
            initialfile=initial_name,
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            confirmoverwrite=True,
        )
        if not path:
            self.template_status_var.set("저장 취소")
            return
        try:
            save_preset(path, self.state.preset)
            self.state.template_path = path
            self._refresh_template_ui()
            self.template_status_var.set(f"저장 완료: {path}")
            logging.info("템플릿 저장: %s", path)
        except Exception as exc:
            logging.exception("템플릿 저장 실패: %s", exc)
            messagebox.showerror("템플릿", f"저장 실패: {exc}")

    def _validate_template(self, *, show_success: bool = True) -> bool:
        if self.template_editor:
            self.template_editor.flush_pending_edits()
        try:
            validate_preset_for_ui(self.state.preset)
        except Exception as exc:
            msg = f"템플릿 유효성 검증 실패: {exc}"
            self.template_status_var.set(msg)
            messagebox.showerror("템플릿", msg)
            logging.warning(msg)
            return False

        self.template_status_var.set("템플릿 유효성 검증 통과")
        logging.info("템플릿 유효성 검증 통과")
        if show_success:
            messagebox.showinfo("템플릿", "템플릿 유효성 검증 통과")
        return True

    def _pick_build_folder(self) -> None:
        path = filedialog.askdirectory(title="이미지 폴더 선택")
        if path:
            self.build_folder_var.set(path)

    def _pick_build_preset_json(self) -> None:
        path = filedialog.askopenfilename(
            title="NAIS/SDStudio 프리셋 JSON 선택",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.build_preset_json_var.set(path)

    def _apply_generated_variable(self, variable, stats: dict, *, status_prefix: str) -> None:
        variables = [v for v in self.state.preset.variables if v.name != variable.name]
        variables.append(variable)
        preset_name = self.state.preset.name or self.state.get_template_name()
        self.state.preset = Preset(name=preset_name, variables=variables)
        self._refresh_template_ui()
        self.template_status_var.set(status_prefix)
        logging.info("변수 생성 완료: %s stats=%s", variable.name, stats)

    def _build_variable(self) -> None:
        folder = self.build_folder_var.get().strip()
        if not folder:
            messagebox.showwarning("변수 생성", "이미지 폴더를 선택하세요.")
            return
        variable_name = self.build_variable_var.get().strip() or None
        include_negative = bool(self.build_include_negative_var.get())
        self.template_status_var.set("변수 생성 중...")

        def work(progress_cb, cancel_cb):
            return build_variable_from_folder(
                folder,
                variable_name=variable_name,
                include_negative=include_negative,
                progress_cb=progress_cb,
            )

        def done(payload):
            variable, stats = payload
            self._apply_generated_variable(
                variable,
                stats,
                status_prefix=(
                f"생성 완료: {variable.name} ({len(variable.values)} values, "
                f"공통태그 {stats.get('common_count', 0)}개)"
                ),
            )

        self._run_async("템플릿 생성", work, done, self.template_status_var)

    def _build_variable_from_json(self) -> None:
        json_path = self.build_preset_json_var.get().strip()
        if not json_path:
            messagebox.showwarning("변수 생성", "프리셋 JSON 파일을 선택하세요.")
            return
        variable_name = self.build_variable_var.get().strip() or None
        self.template_status_var.set("JSON 기반 변수 생성 중...")

        def work(progress_cb, cancel_cb):
            return build_variable_from_preset_json(
                json_path,
                variable_name=variable_name,
            )

        def done(payload):
            variable, stats = payload
            self._apply_generated_variable(
                variable,
                stats,
                status_prefix=(
                    f"생성 완료: {variable.name} "
                    f"(import {stats.get('imported_values', len(variable.values))}/"
                    f"{stats.get('total_values', len(variable.values))}, "
                    f"빈태그제외 {stats.get('removed_empty', 0)}, "
                    f"충돌제외 {stats.get('removed_conflicts', 0)})"
                ),
            )

        self._run_async("JSON 템플릿 생성", work, done, self.template_status_var)

    def _fill_rename_order(self) -> None:
        names = [var.name for var in self.state.preset.variables]
        self.rename_order_var.set(",".join(names))

    def _fill_move_order(self) -> None:
        names = [var.name for var in self.state.preset.variables]
        self.move_order_var.set(",".join(names))
