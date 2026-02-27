from __future__ import annotations

import tkinter as tk


class ResultPanelListMixin:
    def _cancel_list_fill(self) -> None:
        if self.list_fill_after_id:
            try:
                self.parent.after_cancel(self.list_fill_after_id)
            except Exception:
                pass
            self.list_fill_after_id = None

    def _start_list_fill(self, target_list_idx: int) -> None:
        self._cancel_list_fill()
        self.listbox.delete(0, tk.END)
        self.list_fill_cursor = 0
        if self.filtered_indices:
            self.list_fill_target_idx = max(0, min(target_list_idx, len(self.filtered_indices) - 1))
        else:
            self.list_fill_target_idx = 0
        self._fill_listbox_chunk()

    def _fill_listbox_chunk(self) -> None:
        total = len(self.filtered_indices)
        if total <= 0:
            return
        start = self.list_fill_cursor
        end = min(total, start + self.list_insert_batch)
        batch = [self._to_text(self.records[idx]) for idx in self.filtered_indices[start:end]]
        if batch:
            self.listbox.insert(tk.END, *batch)
        self.list_fill_cursor = end
        if end < total:
            self.list_fill_after_id = self.parent.after(1, self._fill_listbox_chunk)
            return
        self.list_fill_after_id = None
        self._select_list_index(self.list_fill_target_idx)

    def _select_list_index(self, list_idx: int) -> None:
        if list_idx < 0 or list_idx >= len(self.filtered_indices):
            return
        if list_idx >= int(self.listbox.size()):
            return
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(list_idx)
        self.listbox.activate(list_idx)
        self.listbox.see(list_idx)
        self._on_select(None)

    def _on_select(self, _event: tk.Event | None) -> None:
        selected = self.listbox.curselection()
        if not selected:
            return
        list_idx = int(selected[0])
        if list_idx >= len(self.filtered_indices):
            return
        record_idx = self.filtered_indices[list_idx]
        self._set_selected_record(record_idx, sync_list=False)

    def _set_selected_record(self, record_idx: int, *, sync_list: bool) -> None:
        if record_idx < 0 or record_idx >= len(self.records):
            return
        self.selected_record_idx = record_idx
        record = self.records[record_idx]
        self.preview_path = self._record_preview_path(record)
        self.preview_path_var.set(self.preview_path)
        if sync_list:
            try:
                list_idx = self.filtered_indices.index(record_idx)
            except ValueError:
                list_idx = -1
            if list_idx >= 0:
                if list_idx < int(self.listbox.size()):
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(list_idx)
                    self.listbox.activate(list_idx)
                    self.listbox.see(list_idx)
                else:
                    self.list_fill_target_idx = list_idx
        # 좌측 선택 기준으로 우측 썸네일을 주변 이미지 포함 형태로 다시 구성한다.
        self._render_thumbnail_grid()

    def _on_thumbnail_click(self, record_idx: int) -> None:
        self._set_selected_record(record_idx, sync_list=True)
