from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class LayoutMixin:
    def _build(self, parent: ttk.Frame) -> None:
        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.pane = pane
        pane.bind("<Configure>", self._on_pane_configure)

        var_frame = ttk.Labelframe(pane, text="변수")
        self.var_listbox = tk.Listbox(var_frame, exportselection=False)
        self.var_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.var_listbox.bind("<<ListboxSelect>>", self._on_variable_select)
        self.var_listbox.bind("<Double-ButtonRelease-1>", self._begin_variable_inline_edit)
        self.var_listbox.bind("<F2>", self._edit_selected_variable)
        self.var_listbox.bind("<Button-3>", self._show_variable_context_menu)
        self.variable_context_menu = tk.Menu(var_frame, tearoff=0)
        self.variable_context_menu.add_command(label="변수 추가", command=self._add_variable)
        self.variable_context_menu.add_command(label="선택 변수 삭제", command=self._delete_variable)

        pane.add(var_frame, weight=1)

        value_frame = ttk.Labelframe(pane, text="값")
        value_pane = ttk.PanedWindow(value_frame, orient=tk.HORIZONTAL)
        value_pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.value_pane = value_pane
        value_pane.bind("<Configure>", self._on_value_pane_configure)

        values_box = ttk.Labelframe(value_pane, text="값 목록")
        self.value_listbox = tk.Listbox(values_box, selectmode=tk.EXTENDED, exportselection=False)
        self.value_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 4))
        self.value_listbox.bind("<<ListboxSelect>>", self._on_value_select)
        self.value_listbox.bind("<Double-ButtonRelease-1>", self._begin_value_inline_edit)
        self.value_listbox.bind("<F2>", self._edit_selected_value)
        self.value_listbox.bind("<Button-3>", self._show_value_context_menu)
        self.value_context_menu = tk.Menu(values_box, tearoff=0)
        self.value_context_menu.add_command(label="값 추가", command=self._add_value)
        self.value_context_menu.add_command(label="선택 반전", command=self._invert_value_selection)
        self.value_context_menu.add_command(label="선택 값 삭제", command=self._delete_value)

        ttk.Label(values_box, text="값 검색").pack(anchor="w", padx=6)
        value_search_row = ttk.Frame(values_box)
        value_search_row.pack(fill=tk.X, padx=6, pady=(0, 6))
        value_search_row.columnconfigure(0, weight=1)
        self.value_search_combo = ttk.Combobox(
            value_search_row,
            textvariable=self.value_search_var,
            state="normal",
        )
        self.value_search_combo.grid(row=0, column=0, sticky="we", padx=(0, 6))
        self.value_search_combo.bind("<KeyRelease>", self._on_value_search_key_release)
        self.value_search_combo.bind("<<ComboboxSelected>>", self._on_value_search_commit)
        self.value_search_combo.bind("<Return>", self._on_value_search_commit)
        ttk.Checkbutton(
            value_search_row,
            text="정규식",
            variable=self.value_search_regex_var,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(value_search_row, text="검색", command=self._select_value_by_query).grid(
            row=0, column=2
        )

        value_edit = ttk.Frame(values_box)
        value_edit.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(value_edit, text="일괄 이름 변경/치환").pack(anchor="w")
        ttk.Entry(value_edit, textvariable=self.value_name_var).pack(fill=tk.X, pady=(0, 6))
        value_buttons = ttk.Frame(value_edit)
        value_buttons.pack(fill=tk.X)
        self.value_add_mode_combo = ttk.Combobox(
            value_buttons,
            textvariable=self.value_add_mode_var,
            state="readonly",
            values=("뒤에 추가", "앞에 추가"),
            width=10,
        )
        self.value_add_mode_combo.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(value_buttons, text="문자열 추가", command=self._bulk_add_value_text).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(value_buttons, text="문자열 삭제", command=self._bulk_remove_value_text).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(value_buttons, text="정규식 치환", command=self._bulk_regex_replace_value_text).pack(
            side=tk.LEFT
        )

        tag_box = ttk.Labelframe(value_pane, text="선택 값 태그")
        self.tag_listbox = tk.Listbox(
            tag_box,
            selectmode=tk.EXTENDED,
            height=6,
            exportselection=False,
        )
        self.tag_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 4))
        self.tag_listbox.bind("<Double-ButtonRelease-1>", self._begin_tag_inline_edit)
        self.tag_listbox.bind("<F2>", self._edit_selected_tag)
        self.tag_listbox.bind("<Button-3>", self._show_tag_context_menu)
        self.tag_context_menu = tk.Menu(tag_box, tearoff=0)
        self.tag_context_menu.add_command(label="태그 추가", command=self._begin_new_tag_inline)
        self.tag_context_menu.add_command(label="선택 반전", command=self._invert_tag_selection)
        self.tag_context_menu.add_command(label="선택 태그 삭제", command=self._delete_selected_tags)

        tag_edit = ttk.Frame(tag_box)
        tag_edit.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(tag_edit, text="태그 검색").pack(anchor="w")
        tag_search_row = ttk.Frame(tag_edit)
        tag_search_row.pack(fill=tk.X, pady=(0, 6))
        tag_search_row.columnconfigure(0, weight=1)
        self.tag_search_combo = ttk.Combobox(
            tag_search_row,
            textvariable=self.tag_search_var,
            state="normal",
        )
        self.tag_search_combo.grid(row=0, column=0, sticky="we", padx=(0, 6))
        self.tag_search_combo.bind("<KeyRelease>", self._on_tag_search_key_release)
        self.tag_search_combo.bind("<<ComboboxSelected>>", self._on_tag_search_commit)
        self.tag_search_combo.bind("<Return>", self._on_tag_search_commit)
        ttk.Checkbutton(
            tag_search_row,
            text="정규식",
            variable=self.tag_search_regex_var,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(tag_search_row, text="검색", command=self._select_tags_by_query).grid(
            row=0, column=2, padx=(0, 4)
        )
        ttk.Button(
            tag_search_row,
            text="값 정규식 가져오기",
            command=self._copy_value_regex_to_tag_regex,
        ).grid(row=0, column=3)
        ttk.Label(tag_edit, text="일괄 이름 변경/치환").pack(anchor="w")
        ttk.Entry(tag_edit, textvariable=self.tag_input_var).pack(fill=tk.X, pady=(0, 6))

        tag_buttons = ttk.Frame(tag_edit)
        tag_buttons.pack(fill=tk.X)
        ttk.Button(tag_buttons, text="문자열 추가", command=self._bulk_add_tags_to_values).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(tag_buttons, text="문자열 삭제", command=self._bulk_remove_tags_from_values).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.tag_replace_mode_combo = ttk.Combobox(
            tag_buttons,
            textvariable=self.tag_replace_mode_var,
            state="readonly",
            values=(
                "태그 정규식 치환",
                "현재 값 내에서 태그 교체",
                "현재 변수 전체에서 태그 교체",
            ),
            width=20,
        )
        self.tag_replace_mode_combo.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tag_buttons, text="정규식 치환", command=self._run_tag_regex_action).pack(
            side=tk.LEFT
        )
        value_pane.add(values_box, weight=1)
        value_pane.add(tag_box, weight=2)
        pane.add(value_frame, weight=2)
        parent.after(120, self._set_initial_sash)
        value_frame.after(120, self._set_value_initial_sash)

    def _on_pane_configure(self, _event: tk.Event) -> None:
        if self.pane and not getattr(self.pane, "_initial_sash_set", False):
            self._set_initial_sash()
        self._repair_collapsed_sash(self.pane, self.var_ratio, min_left=220, min_right=420)

    def _on_value_pane_configure(self, _event: tk.Event) -> None:
        if self.value_pane and not getattr(self.value_pane, "_initial_sash_set", False):
            self._set_value_initial_sash()
        self._repair_collapsed_sash(
            self.value_pane,
            self.value_ratio,
            min_left=220,
            min_right=360,
        )

    def _set_initial_sash(self) -> None:
        self._set_sash_once(self.pane, self.var_ratio, min_left=220, min_right=420)

    def _set_value_initial_sash(self) -> None:
        self._set_sash_once(self.value_pane, self.value_ratio, min_left=220, min_right=360)

    def _set_sash_once(
        self,
        pane: ttk.PanedWindow | None,
        ratio: float,
        *,
        min_left: int,
        min_right: int,
    ) -> None:
        if not pane:
            return
        width = pane.winfo_width()
        if width <= (min_left + min_right):
            return
        target = int(width * ratio)
        target = max(min_left, min(target, width - min_right))
        if target <= 0 or target >= width:
            return
        pane.sashpos(0, target)
        setattr(pane, "_initial_sash_set", True)

    def _repair_collapsed_sash(
        self,
        pane: ttk.PanedWindow | None,
        ratio: float,
        *,
        min_left: int,
        min_right: int,
    ) -> None:
        if not pane or not getattr(pane, "_initial_sash_set", False):
            return
        width = pane.winfo_width()
        if width <= (min_left + min_right):
            return
        try:
            pos = int(pane.sashpos(0))
        except Exception:
            return
        # 초기 렌더 타이밍 문제로 분할선이 극단으로 붙는 경우만 자동 복구
        if 0 <= pos <= 20 or pos >= (width - 20):
            target = int(width * ratio)
            target = max(min_left, min(target, width - min_right))
            if 0 < target < width:
                pane.sashpos(0, target)
