from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.preset import Preset

from .actions_mixin import ActionsMixin
from .bulk import BulkOpsMixin
from .inline import InlineEditMixin
from .layout_mixin import LayoutMixin
from .search_mixin import SearchMixin


GetPresetFn = Callable[[], Preset]
SetPresetFn = Callable[[Preset], None]
StatusFn = Callable[[str], None]
ChangedFn = Callable[[], None]


class TemplateEditorPanel(
    ActionsMixin,
    LayoutMixin,
    InlineEditMixin,
    SearchMixin,
    BulkOpsMixin,
):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        get_preset: GetPresetFn,
        set_preset: SetPresetFn,
        set_status: StatusFn,
        on_changed: ChangedFn | None = None,
    ) -> None:
        self.get_preset = get_preset
        self.set_preset = set_preset
        self.set_status = set_status
        self.on_changed = on_changed

        self.variable_name_var = tk.StringVar(value="")
        self.value_name_var = tk.StringVar(value="")
        self.value_search_var = tk.StringVar(value="")
        self.value_search_regex_var = tk.BooleanVar(value=False)
        self.tag_search_var = tk.StringVar(value="")
        self.tag_search_regex_var = tk.BooleanVar(value=False)
        self.tag_input_var = tk.StringVar(value="")
        self.tag_replace_mode_var = tk.StringVar(value="태그 정규식 치환")

        self.var_listbox: tk.Listbox | None = None
        self.variable_context_menu: tk.Menu | None = None
        self.value_listbox: tk.Listbox | None = None
        self.tag_listbox: tk.Listbox | None = None
        self.value_search_combo: tk.Entry | None = None
        self.value_search_candidates: list[str] = []
        self.tag_search_combo: tk.Entry | None = None
        self.tag_search_candidates: list[str] = []
        self.tag_replace_mode_combo: ttk.Combobox | None = None
        self.value_context_menu: tk.Menu | None = None
        self.tag_context_menu: tk.Menu | None = None
        self.value_pane: ttk.PanedWindow | None = None
        self.pane: ttk.PanedWindow | None = None
        self.var_ratio = 0.19
        self.value_ratio = 0.32

        self.inline_entry: tk.Entry | None = None
        self.inline_mode: str | None = None
        self.inline_index: int | None = None
        self.inline_ignore_focus_out = False

        self._build(parent)
