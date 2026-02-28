from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox

from core.preset import Preset

from .ops import normalize_tags_input, update_value
from .validation import validate_value_tag_constraints


def apply_value_name_add_mode(value_name: str, text: str, mode: str) -> str:
    if mode == "앞에 추가":
        return f"{text}{value_name}"
    return f"{value_name}{text}"


class BulkOpsMixin:
    def _replace_variable_values(
        self,
        var_idx: int,
        new_values: list[dict[str, object]],
        message: str,
    ) -> None:
        preset = self.get_preset()
        payload = preset.model_dump()
        variables = payload.get("variables", [])
        if var_idx < 0 or var_idx >= len(variables):
            return
        variables[var_idx]["values"] = new_values
        try:
            validate_value_tag_constraints(variables[var_idx]["values"])
            new_preset = Preset.model_validate(payload)
            self._apply_preset(new_preset, message)
        except Exception as exc:
            messagebox.showerror("템플릿", f"일괄 작업 실패: {exc}")

    @staticmethod
    def _compile_regex_or_warn(pattern_text: str) -> re.Pattern[str] | None:
        if not pattern_text:
            messagebox.showwarning("템플릿", "정규식 패턴을 입력하세요.")
            return None
        try:
            return re.compile(pattern_text)
        except re.error as exc:
            messagebox.showerror("템플릿", f"정규식 오류: {exc}")
            return None

    def _bulk_add_value_text(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        text = self.value_name_var.get()
        if not text:
            messagebox.showwarning("템플릿", "추가할 문자열을 입력하세요.")
            return
        mode_var = getattr(self, "value_add_mode_var", None)
        mode = mode_var.get().strip() if mode_var else "뒤에 추가"
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        changed = 0
        for value in variable.values:
            new_name = apply_value_name_add_mode(value.name, text, mode)
            if new_name != value.name:
                changed += 1
            new_values.append({"name": new_name, "tags": list(value.tags)})
        if changed == 0:
            self.set_status(f"값 이름 일괄 추가({mode}): 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"값 이름 일괄 추가({mode}): {changed}개 변경",
        )

    def _bulk_remove_value_text(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        text = self.value_name_var.get()
        if not text:
            messagebox.showwarning("템플릿", "삭제할 문자열을 입력하세요.")
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        changed = 0
        empty_name_count = 0
        for value in variable.values:
            new_name = value.name.replace(text, "")
            if new_name != value.name:
                changed += 1
            if not new_name.strip():
                empty_name_count += 1
            new_values.append({"name": new_name, "tags": list(value.tags)})
        if empty_name_count > 0:
            messagebox.showwarning(
                "템플릿",
                f"삭제 결과 빈 값 이름이 {empty_name_count}개 발생하여 중단했습니다.",
            )
            return
        if changed == 0:
            self.set_status("값 이름 일괄 삭제: 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"값 이름 일괄 삭제: {changed}개 변경",
        )

    def _bulk_regex_replace_value_text(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        pattern_text = self.value_search_var.get().strip()
        if not bool(self.value_search_regex_var.get()):
            messagebox.showwarning("템플릿", "값 검색의 '정규식' 체크를 켜세요.")
            return
        replace_text = self.value_name_var.get()
        pattern = self._compile_regex_or_warn(pattern_text)
        if pattern is None:
            return

        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        changed = 0
        empty_name_count = 0
        for value in variable.values:
            new_name = pattern.sub(replace_text, value.name)
            if new_name != value.name:
                changed += 1
            if not new_name.strip():
                empty_name_count += 1
            new_values.append({"name": new_name, "tags": list(value.tags)})

        if empty_name_count > 0:
            messagebox.showwarning(
                "템플릿",
                f"치환 결과 빈 값 이름이 {empty_name_count}개 발생하여 중단했습니다.",
            )
            return
        if changed == 0:
            self.set_status("값 이름 정규식 치환: 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"값 이름 정규식 치환: {changed}개 변경",
        )

    def _copy_value_regex_to_tag_regex(self) -> None:
        pattern_text = self.value_search_var.get().strip()
        if not pattern_text:
            messagebox.showwarning("템플릿", "값 쪽 정규식 패턴이 비어 있습니다.")
            return
        self.tag_search_var.set(pattern_text)
        self.tag_search_regex_var.set(True)
        self.set_status("값 검색 정규식을 태그 검색 정규식으로 복사했습니다.")

    def _derive_tags_from_value_name(
        self,
        value_name: str,
        pattern: re.Pattern[str],
        replace_text: str,
    ) -> tuple[bool, list[str]]:
        matched = pattern.search(value_name)
        if not matched:
            return False, []
        try:
            rendered = matched.expand(replace_text)
        except re.error as exc:
            messagebox.showerror("템플릿", f"치환식 오류: {exc}")
            return False, []
        return True, normalize_tags_input(rendered)

    def _replace_selected_tags_from_value_regex(self) -> None:
        var_idx = self._selected_var_index()
        value_idx = self._selected_value_index()
        if var_idx is None or value_idx is None:
            messagebox.showwarning("템플릿", "값을 먼저 선택하세요.")
            return
        if not bool(self.value_search_regex_var.get()):
            messagebox.showwarning("템플릿", "값 검색의 '정규식' 체크를 켜세요.")
            return
        pattern = self._compile_regex_or_warn(self.value_search_var.get().strip())
        if pattern is None:
            return
        replace_text = self.tag_input_var.get()
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        if value_idx >= len(variable.values):
            return
        value = variable.values[value_idx]
        ok, new_tags = self._derive_tags_from_value_name(value.name, pattern, replace_text)
        if not ok:
            messagebox.showwarning("템플릿", "선택 값 이름이 정규식과 매치되지 않습니다.")
            return
        if new_tags == list(value.tags):
            self.set_status("값 기반 태그 교체: 변경 없음")
            return
        try:
            new_preset = update_value(preset, var_idx, value_idx, value.name, new_tags)
            self._apply_preset(
                new_preset,
                f"값 기반 태그 교체: {value.name} ({len(new_tags)}개)",
            )
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _replace_variable_tags_from_value_regex(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        if not bool(self.value_search_regex_var.get()):
            messagebox.showwarning("템플릿", "값 검색의 '정규식' 체크를 켜세요.")
            return
        pattern = self._compile_regex_or_warn(self.value_search_var.get().strip())
        if pattern is None:
            return
        replace_text = self.tag_input_var.get()
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        matched_count = 0
        changed_count = 0
        for value in variable.values:
            ok, new_tags = self._derive_tags_from_value_name(value.name, pattern, replace_text)
            if ok:
                matched_count += 1
                if new_tags != list(value.tags):
                    changed_count += 1
                new_values.append({"name": value.name, "tags": new_tags})
            else:
                new_values.append({"name": value.name, "tags": list(value.tags)})
        if matched_count == 0:
            messagebox.showwarning("템플릿", "현재 변수에서 정규식과 매치되는 값이 없습니다.")
            return
        if changed_count == 0:
            self.set_status("값 기반 태그 교체(현재 변수): 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"값 기반 태그 교체(현재 변수): {changed_count}개 값 변경",
        )

    def _bulk_add_tags_to_values(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        tags_to_add = normalize_tags_input(self.tag_input_var.get())
        if not tags_to_add:
            messagebox.showwarning("템플릿", "삽입할 태그를 입력하세요.")
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        changed = 0
        for value in variable.values:
            merged = list(value.tags)
            for tag in tags_to_add:
                if tag not in merged:
                    merged.append(tag)
            if merged != list(value.tags):
                changed += 1
            new_values.append({"name": value.name, "tags": merged})
        if changed == 0:
            self.set_status("태그 일괄 삽입: 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"태그 일괄 삽입: {changed}개 값 변경",
        )

    def _bulk_remove_tags_from_values(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        tags_to_remove = set(normalize_tags_input(self.tag_input_var.get()))
        if not tags_to_remove:
            messagebox.showwarning("템플릿", "삭제할 태그를 입력하세요.")
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        changed = 0
        for value in variable.values:
            updated = [tag for tag in value.tags if tag not in tags_to_remove]
            if updated != list(value.tags):
                changed += 1
            new_values.append({"name": value.name, "tags": updated})
        if changed == 0:
            self.set_status("태그 일괄 삭제: 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"태그 일괄 삭제: {changed}개 값 변경",
        )

    @staticmethod
    def _dedupe_keep_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    def _run_tag_regex_action(self) -> None:
        mode = self.tag_replace_mode_var.get().strip()
        if mode == "현재 값 내에서 태그 교체":
            self._replace_selected_tags_from_value_regex()
            return
        if mode == "현재 변수 전체에서 태그 교체":
            self._replace_variable_tags_from_value_regex()
            return
        self._bulk_regex_replace_tags()

    def _bulk_regex_replace_tags(self) -> None:
        var_idx = self._selected_var_index()
        if var_idx is None:
            messagebox.showwarning("템플릿", "변수를 먼저 선택하세요.")
            return
        pattern_text = self.tag_search_var.get().strip()
        if not bool(self.tag_search_regex_var.get()):
            messagebox.showwarning("템플릿", "태그 검색의 '정규식' 체크를 켜세요.")
            return
        replace_text = self.tag_input_var.get()
        pattern = self._compile_regex_or_warn(pattern_text)
        if pattern is None:
            return

        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        variable = preset.variables[var_idx]
        new_values: list[dict[str, object]] = []
        changed = 0

        for value in variable.values:
            replaced_tags: list[str] = []
            for tag in value.tags:
                after = pattern.sub(replace_text, tag)
                replaced_tags.extend(normalize_tags_input(after))
            replaced_tags = self._dedupe_keep_order(replaced_tags)
            if replaced_tags != list(value.tags):
                changed += 1
            new_values.append({"name": value.name, "tags": replaced_tags})

        if changed == 0:
            self.set_status("태그 정규식 치환: 변경 없음")
            return
        self._replace_variable_values(
            var_idx,
            new_values,
            f"태그 정규식 치환: {changed}개 값 변경",
        )
