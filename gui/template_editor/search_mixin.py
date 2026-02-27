from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from core.preset import Preset

from .ops import normalize_tags_input
from .search import (
    build_tag_candidates,
    build_value_candidates,
    filter_suggestions,
    find_best_value_match_index,
    find_tag_match_indices,
)


class SearchMixin:
    def _refresh_value_search_candidates(self, preset: Preset, var_idx: int | None) -> None:
        if not self.value_search_combo:
            return
        if var_idx is None or var_idx < 0 or var_idx >= len(preset.variables):
            self.value_search_candidates = []
            self.value_search_combo.configure(values=[])
            return
        self.value_search_candidates = build_value_candidates(preset.variables[var_idx])
        self._update_value_search_suggestions(self.value_search_var.get())

    def _update_value_search_suggestions(self, query: str) -> None:
        if not self.value_search_combo:
            return
        values = filter_suggestions(self.value_search_candidates, query, csv_mode=False, limit=300)
        self.value_search_combo.configure(values=values)

    def _on_value_search_key_release(self, _event: tk.Event) -> None:
        self._update_value_search_suggestions(self.value_search_var.get())

    def _on_value_search_commit(self, _event: tk.Event) -> str:
        self._select_value_by_query()
        return "break"

    def _select_value_by_query(self) -> None:
        if not self.value_listbox:
            return
        query = self.value_search_var.get().strip()
        if not query:
            messagebox.showwarning("템플릿", "검색할 값을 입력하세요.")
            return
        size = int(self.value_listbox.size())
        if size <= 0:
            return

        items = [str(self.value_listbox.get(idx)) for idx in range(size)]
        target_idx = find_best_value_match_index(items, query)
        if target_idx < 0:
            self.set_status("값 검색 이동: 매치 없음")
            return
        self.value_listbox.selection_clear(0, tk.END)
        self.value_listbox.selection_set(target_idx)
        self.value_listbox.activate(target_idx)
        self.value_listbox.see(target_idx)
        self._on_value_select(None)
        self.set_status(f"값 검색 이동: {self.value_listbox.get(target_idx)}")

    def _refresh_tag_search_candidates(self, preset: Preset, var_idx: int | None) -> None:
        if not self.tag_search_combo:
            return
        if var_idx is None or var_idx < 0 or var_idx >= len(preset.variables):
            self.tag_search_candidates = []
            self.tag_search_combo.configure(values=[])
            return

        self.tag_search_candidates = build_tag_candidates(preset.variables[var_idx])
        self._update_tag_search_suggestions(self.tag_search_var.get())

    def _update_tag_search_suggestions(self, query: str) -> None:
        if not self.tag_search_combo:
            return
        values = filter_suggestions(self.tag_search_candidates, query, csv_mode=True, limit=300)
        self.tag_search_combo.configure(values=values)

    def _on_tag_search_key_release(self, _event: tk.Event) -> None:
        self._update_tag_search_suggestions(self.tag_search_var.get())

    def _on_tag_search_commit(self, _event: tk.Event) -> str:
        self._select_tags_by_query()
        return "break"

    def _select_tags_by_query(self) -> None:
        if not self.tag_listbox:
            return
        raw = self.tag_search_var.get().strip()
        queries = normalize_tags_input(raw)
        if not queries:
            messagebox.showwarning("템플릿", "검색할 태그를 입력하세요.")
            return
        size = int(self.tag_listbox.size())
        tags = [str(self.tag_listbox.get(idx)) for idx in range(size)]
        matched_indices = find_tag_match_indices(tags, queries)

        self.tag_listbox.selection_clear(0, tk.END)
        for idx in matched_indices:
            self.tag_listbox.selection_set(idx)
        if matched_indices:
            self.tag_listbox.activate(matched_indices[0])
            self.tag_listbox.see(matched_indices[0])
            self.set_status(f"태그 검색 선택: {len(matched_indices)}개 매치")
        else:
            self.set_status("태그 검색 선택: 매치 없음")

    def _invert_tag_selection(self) -> None:
        if not self.tag_listbox:
            return
        size = int(self.tag_listbox.size())
        if size <= 0:
            return
        selected = set(self._selected_tag_indices())
        for idx in range(size):
            if idx in selected:
                self.tag_listbox.selection_clear(idx)
            else:
                self.tag_listbox.selection_set(idx)
        self.set_status(f"태그 선택 반전: {len(selected)} -> {size - len(selected)}")
