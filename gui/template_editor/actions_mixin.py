from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from core.preset import Preset

from .ops import (
    add_value,
    add_variable,
    delete_value,
    delete_variable,
    normalize_tags_input,
    rename_variable,
    update_value,
)
from .validation import validate_value_tag_constraints


class ActionsMixin:
    def refresh(self) -> None:
        self._end_inline_edit(commit=False)
        preset = self.get_preset()
        self._refresh_variable_list(preset)
        self._refresh_value_list(preset)

    def _refresh_variable_list(self, preset: Preset) -> None:
        if not self.var_listbox:
            return
        if self.inline_mode == "variable":
            self._end_inline_edit(commit=False)
        selected = self.var_listbox.curselection()
        selected_idx = selected[0] if selected else 0

        self.var_listbox.delete(0, tk.END)
        for variable in preset.variables:
            self.var_listbox.insert(tk.END, f"{variable.name} ({len(variable.values)} 값)")

        if preset.variables:
            selected_idx = max(0, min(selected_idx, len(preset.variables) - 1))
            self.var_listbox.selection_set(selected_idx)
            self.var_listbox.activate(selected_idx)
            self.variable_name_var.set(preset.variables[selected_idx].name)
        else:
            self.variable_name_var.set("")

    def _refresh_value_list(self, preset: Preset) -> None:
        if not self.value_listbox:
            return
        if self.inline_mode in ("value", "tag"):
            self._end_inline_edit(commit=False)
        selected = self.value_listbox.curselection()
        selected_idx = selected[0] if selected else 0
        self.value_listbox.delete(0, tk.END)
        var_idx = self._selected_var_index()
        if var_idx is None:
            self._clear_value_inputs()
            self._refresh_value_search_candidates(preset, None)
            self._refresh_tag_search_candidates(preset, None)
            return
        if var_idx >= len(preset.variables):
            self._clear_value_inputs()
            self._refresh_value_search_candidates(preset, None)
            self._refresh_tag_search_candidates(preset, None)
            return

        variable = preset.variables[var_idx]
        self._refresh_value_search_candidates(preset, var_idx)
        self._refresh_tag_search_candidates(preset, var_idx)
        for value in variable.values:
            self.value_listbox.insert(tk.END, value.name)

        if variable.values:
            selected_idx = max(0, min(selected_idx, len(variable.values) - 1))
            self.value_listbox.selection_set(selected_idx)
            self.value_listbox.activate(selected_idx)
            self._load_selected_value(preset, var_idx, selected_idx)
        else:
            self._clear_value_inputs()

    def _refresh_tag_list(self, tags: list[str]) -> None:
        if not self.tag_listbox:
            return
        if self.inline_mode == "tag":
            self._end_inline_edit(commit=False)
        self.tag_listbox.delete(0, tk.END)
        for tag in tags:
            self.tag_listbox.insert(tk.END, tag)

    def _selected_var_index(self) -> int | None:
        if not self.var_listbox:
            return None
        selected = self.var_listbox.curselection()
        if selected:
            return int(selected[0])
        size = int(self.var_listbox.size())
        if size <= 0:
            return None
        active = int(self.var_listbox.index("active"))
        if 0 <= active < size:
            return active
        return 0

    def _selected_value_index(self) -> int | None:
        selected = self._selected_value_indices()
        if not selected:
            return None
        return selected[0]

    def _selected_value_indices(self) -> list[int]:
        if not self.value_listbox:
            return []
        selected = [int(i) for i in self.value_listbox.curselection()]
        if selected:
            try:
                active = int(self.value_listbox.index("active"))
                if active in selected:
                    return [active, *[idx for idx in selected if idx != active]]
            except Exception:
                pass
            return selected
        size = int(self.value_listbox.size())
        if size <= 0:
            return []
        active = int(self.value_listbox.index("active"))
        if 0 <= active < size:
            return [active]
        return [0]

    def _selected_tag_indices(self) -> list[int]:
        if not self.tag_listbox:
            return []
        return [int(i) for i in self.tag_listbox.curselection()]

    def _load_selected_value(self, preset: Preset, var_idx: int, value_idx: int) -> None:
        if var_idx < 0 or var_idx >= len(preset.variables):
            self._clear_value_inputs()
            return
        values = preset.variables[var_idx].values
        if value_idx < 0 or value_idx >= len(values):
            self._clear_value_inputs()
            return
        value = values[value_idx]
        self.value_name_var.set(value.name)
        self._refresh_tag_list(value.tags)

    def _apply_preset(self, preset: Preset, message: str) -> None:
        self.set_preset(preset)
        self.refresh()
        self.set_status(message)
        if self.on_changed:
            self.on_changed()

    def _add_variable(self) -> None:
        name = self.variable_name_var.get().strip()
        try:
            new_preset = add_variable(self.get_preset(), name)
            self._apply_preset(new_preset, f"변수 추가: {name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _rename_variable(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 선택하세요.")
            return
        name = self.variable_name_var.get().strip()
        try:
            new_preset = rename_variable(self.get_preset(), var_idx, name)
            self._apply_preset(new_preset, f"변수 이름 변경: {name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _delete_variable(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 선택하세요.")
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        var_name = preset.variables[var_idx].name
        if not messagebox.askyesno("템플릿", f"변수 '{var_name}'를 삭제할까요?"):
            return
        try:
            new_preset = delete_variable(preset, var_idx)
            self._apply_preset(new_preset, f"변수 삭제: {var_name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _add_value(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        value_name = self.value_name_var.get().strip()
        try:
            new_preset = add_value(self.get_preset(), var_idx, value_name, [])
            self._apply_preset(new_preset, f"값 추가: {value_name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _rename_value(self) -> None:
        var_idx = self._selected_var_index()
        value_idx = self._selected_value_index()
        if var_idx is None or value_idx is None:
            messagebox.showwarning("템플릿", "이름을 변경할 값을 선택하세요.")
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        values = preset.variables[var_idx].values
        if value_idx >= len(values):
            return
        value_name = self.value_name_var.get().strip()
        tags = list(values[value_idx].tags)
        try:
            new_preset = update_value(preset, var_idx, value_idx, value_name, tags)
            self._apply_preset(new_preset, f"값 이름 변경: {value_name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _append_tags(self) -> None:
        var_idx = self._selected_var_index()
        value_indices = self._selected_value_indices()
        if var_idx is None or not value_indices:
            messagebox.showwarning("템플릿", "태그를 추가할 값을 선택하세요. (드래그 다중선택 가능)")
            return
        incoming = normalize_tags_input(self.tag_input_var.get())
        if not incoming:
            messagebox.showwarning("템플릿", "추가할 태그를 입력하세요. (쉼표 구분)")
            return

        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return

        payload = preset.model_dump()
        variables = payload.get("variables", [])
        if var_idx >= len(variables):
            return
        values = variables[var_idx].setdefault("values", [])
        changed = 0
        for value_idx in sorted(set(value_indices)):
            if value_idx < 0 or value_idx >= len(values):
                continue
            current_tags = [str(tag) for tag in (values[value_idx].get("tags") or [])]
            merged = list(current_tags)
            for tag in incoming:
                if tag not in merged:
                    merged.append(tag)
            if merged != current_tags:
                values[value_idx]["tags"] = merged
                changed += 1
        if changed == 0:
            self.set_status("태그 추가: 변경 없음")
            return
        try:
            validate_value_tag_constraints(values)
            new_preset = Preset.model_validate(payload)
            self._apply_preset(
                new_preset,
                f"태그 추가: {changed}개 값 변경 (+{len(incoming)}개 입력)",
            )
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _remove_input_tags(self) -> None:
        var_idx = self._selected_var_index()
        value_indices = self._selected_value_indices()
        if var_idx is None or not value_indices:
            messagebox.showwarning("템플릿", "태그를 삭제할 값을 선택하세요. (드래그 다중선택 가능)")
            return
        tags_to_remove = set(normalize_tags_input(self.tag_input_var.get()))
        if not tags_to_remove:
            messagebox.showwarning("템플릿", "삭제할 태그를 입력하세요. (쉼표 구분)")
            return

        preset = self.get_preset()
        payload = preset.model_dump()
        variables = payload.get("variables", [])
        if var_idx >= len(variables):
            return
        values = variables[var_idx].setdefault("values", [])

        changed = 0
        for value_idx in sorted(set(value_indices)):
            if value_idx < 0 or value_idx >= len(values):
                continue
            current_tags = [str(tag) for tag in (values[value_idx].get("tags") or [])]
            updated = [tag for tag in current_tags if tag not in tags_to_remove]
            if updated != current_tags:
                values[value_idx]["tags"] = updated
                changed += 1
        if changed == 0:
            self.set_status("입력 태그 삭제: 변경 없음")
            return
        try:
            validate_value_tag_constraints(values)
            new_preset = Preset.model_validate(payload)
            self._apply_preset(
                new_preset,
                f"입력 태그 삭제: {changed}개 값 변경 (-{len(tags_to_remove)}개 기준)",
            )
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _delete_selected_tags(self) -> None:
        var_idx = self._selected_var_index()
        value_indices = self._selected_value_indices()
        if var_idx is None or not value_indices:
            messagebox.showwarning("템플릿", "태그를 삭제할 값을 선택하세요.")
            return
        selected_tag_indices = set(self._selected_tag_indices())
        if not selected_tag_indices:
            messagebox.showwarning("템플릿", "삭제할 태그를 선택하세요.")
            return
        if not self.tag_listbox:
            return
        selected_tag_names = {
            str(self.tag_listbox.get(tag_idx)) for tag_idx in selected_tag_indices
        }
        if not selected_tag_names:
            messagebox.showwarning("템플릿", "삭제할 태그를 선택하세요.")
            return

        preset = self.get_preset()
        payload = preset.model_dump()
        variables = payload.get("variables", [])
        if var_idx >= len(variables):
            return
        values = variables[var_idx].setdefault("values", [])
        changed = 0
        for value_idx in sorted(set(value_indices)):
            if value_idx < 0 or value_idx >= len(values):
                continue
            current_tags = [str(tag) for tag in (values[value_idx].get("tags") or [])]
            updated_tags = [tag for tag in current_tags if tag not in selected_tag_names]
            if updated_tags != current_tags:
                values[value_idx]["tags"] = updated_tags
                changed += 1
        if changed == 0:
            self.set_status("선택 태그 삭제: 변경 없음")
            return
        try:
            validate_value_tag_constraints(values)
            new_preset = Preset.model_validate(payload)
            self._apply_preset(new_preset, f"선택 태그 삭제: {changed}개 값 변경")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _delete_value(self) -> None:
        var_idx = self._selected_var_index()
        value_indices = self._selected_value_indices()
        if var_idx is None or not value_indices:
            messagebox.showwarning("템플릿", "삭제할 값을 선택하세요.")
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        valid_indices = sorted(
            {
                idx
                for idx in value_indices
                if isinstance(idx, int) and 0 <= idx < len(variable.values)
            },
            reverse=True,
        )
        if not valid_indices:
            messagebox.showwarning("템플릿", "삭제할 값을 선택하세요.")
            return
        if len(valid_indices) == 1:
            value_name = variable.values[valid_indices[0]].name
            question = f"값 '{value_name}'를 삭제할까요?"
        else:
            question = f"선택한 값 {len(valid_indices)}개를 삭제할까요?"
        if not messagebox.askyesno("템플릿", question):
            return
        try:
            if len(valid_indices) == 1:
                target_idx = valid_indices[0]
                value_name = variable.values[target_idx].name
                new_preset = delete_value(preset, var_idx, target_idx)
                self._apply_preset(new_preset, f"값 삭제: {value_name}")
                return

            payload = preset.model_dump()
            values = payload.get("variables", [])[var_idx].setdefault("values", [])
            for idx in valid_indices:
                values.pop(idx)
            new_preset = Preset.model_validate(payload)
            self._apply_preset(new_preset, f"값 삭제: {len(valid_indices)}개")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _on_variable_select(self, _event: tk.Event) -> None:
        preset = self.get_preset()
        var_idx = self._selected_var_index()
        if var_idx is None or var_idx >= len(preset.variables):
            self._clear_value_inputs()
            self._refresh_value_search_candidates(preset, None)
            self._refresh_tag_search_candidates(preset, None)
            return
        self.variable_name_var.set(preset.variables[var_idx].name)
        self._refresh_value_search_candidates(preset, var_idx)
        self._refresh_tag_search_candidates(preset, var_idx)
        self._refresh_value_list(preset)

    def _on_value_select(self, _event: tk.Event) -> None:
        preset = self.get_preset()
        var_idx = self._selected_var_index()
        value_idx = self._selected_value_index()
        if var_idx is None or value_idx is None:
            return
        self._load_selected_value(preset, var_idx, value_idx)

    def _clear_value_inputs(self) -> None:
        if self.inline_mode in ("value", "tag"):
            self._end_inline_edit(commit=False)
        self.value_name_var.set("")
        self._refresh_tag_list([])

    def _clear_tag_input(self) -> None:
        self.tag_input_var.set("")

    def flush_pending_edits(self) -> None:
        # 저장 전에 인라인 편집이 열려 있으면 현재 입력값을 반영한다.
        if self.inline_entry:
            self._end_inline_edit(commit=True)
