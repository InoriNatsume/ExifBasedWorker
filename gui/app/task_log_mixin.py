from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class TaskLogMixin:
    def _write_task_result_log(self, task: str, results: list[dict], *, header: str = "") -> None:
        if task == "rename":
            self.rename_log_records = list(results)
            self.rename_log_header = header
            self._refresh_rename_log_tree()
        else:
            self.move_log_records = list(results)
            self.move_log_header = header
            self._refresh_move_log_tree()

    def _status_allowed(self, status: str, filter_vars: dict[str, tk.BooleanVar]) -> bool:
        if status in filter_vars:
            return bool(filter_vars[status].get())
        return True

    def _refresh_rename_log_tree(self) -> None:
        self._refresh_task_log_tree(
            tree=self.rename_log_tree,
            records=self.rename_log_records,
            filter_vars=self.rename_log_filter_vars,
            summary_var=self.rename_log_summary_var,
            header=self.rename_log_header,
        )

    def _refresh_move_log_tree(self) -> None:
        self._refresh_task_log_tree(
            tree=self.move_log_tree,
            records=self.move_log_records,
            filter_vars=self.move_log_filter_vars,
            summary_var=self.move_log_summary_var,
            header=self.move_log_header,
        )

    def _refresh_task_log_tree(
        self,
        *,
        tree: ttk.Treeview | None,
        records: list[dict],
        filter_vars: dict[str, tk.BooleanVar],
        summary_var: tk.StringVar,
        header: str,
    ) -> None:
        if not tree:
            return
        filtered_records: list[dict] = []
        for item in records:
            status = str(item.get("status") or "INFO")
            if self._status_allowed(status, filter_vars):
                filtered_records.append(item)

        counts_all = self._status_counts(records)
        summary = (
            f"전체 OK {counts_all['OK']} | UNKNOWN {counts_all['UNKNOWN']} | "
            f"CONFLICT {counts_all['CONFLICT']} | ERROR {counts_all['ERROR']} | "
            f"표시 {len(filtered_records)}/{len(records)}"
        )
        if header:
            summary = f"{summary} | {header}"
        summary_var.set(summary)

        for item_id in tree.get_children():
            tree.delete(item_id)

        for item in filtered_records:
            status = str(item.get("status") or "INFO")
            before = str(item.get("source") or "")
            after = str(item.get("target") or "") or "-"
            detail = str(item.get("message") or "") or "-"
            tree.insert("", tk.END, values=(status, before, after, detail), tags=(status,))
