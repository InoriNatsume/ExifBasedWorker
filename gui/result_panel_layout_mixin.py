from __future__ import annotations

import tkinter as tk


class ResultPanelLayoutMixin:
    def _on_pane_configure(self, _event: tk.Event) -> None:
        if self.pane and not getattr(self.pane, "_initial_sash_set", False):
            self._set_initial_sash()

    def _set_initial_sash(self) -> None:
        if not self.pane:
            return
        width = self.pane.winfo_width()
        if width <= 0:
            return
        self.pane.sashpos(0, int(width * self.list_ratio))
        setattr(self.pane, "_initial_sash_set", True)

    def _on_parent_destroy(self, event: tk.Event) -> None:
        if event.widget is not self.parent:
            return
        if self._closed:
            return
        self._closed = True
        self.thumbnail_executor.shutdown(wait=False, cancel_futures=True)
