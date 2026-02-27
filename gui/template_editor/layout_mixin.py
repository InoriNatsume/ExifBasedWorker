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

        var_edit = ttk.Frame(var_frame)
        var_edit.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Entry(var_edit, textvariable=self.variable_name_var).pack(
            fill=tk.X, expand=True, pady=(0, 6)
        )
        var_buttons = ttk.Frame(var_edit)
        var_buttons.pack(fill=tk.X)
        ttk.Button(var_buttons, text="변수 추가", command=self._add_variable).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(var_buttons, text="변수 삭제", command=self._delete_variable).pack(side=tk.LEFT)
        ttk.Label(var_edit, text="변수 더블클릭으로 이름 수정").pack(anchor="w", pady=(6, 0))
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

        ttk.Label(values_box, text="값 검색 (자동완성)").pack(anchor="w", padx=6)
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
        ttk.Button(value_search_row, text="검색 이동", command=self._select_value_by_query).grid(
            row=0, column=1
        )

        value_edit = ttk.Frame(values_box)
        value_edit.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(value_edit, text="값 이름").pack(anchor="w")
        ttk.Entry(value_edit, textvariable=self.value_name_var).pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            value_edit,
            text="값 더블클릭으로 이름 수정",
        ).pack(anchor="w", pady=(0, 6))

        value_buttons = ttk.Frame(value_edit)
        value_buttons.pack(fill=tk.X)
        ttk.Button(value_buttons, text="값 추가", command=self._add_value).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(value_buttons, text="값 삭제", command=self._delete_value).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(value_buttons, text="입력 초기화", command=self._clear_value_inputs).pack(
            side=tk.LEFT
        )
        ttk.Label(
            value_edit,
            text="값만 추가됩니다. 태그는 오른쪽 입력칸에서 추가하세요.",
        ).pack(anchor="w", pady=(6, 0))

        value_bulk = ttk.Labelframe(value_edit, text="값 이름 일괄 (현재 변수 전체)")
        value_bulk.pack(fill=tk.X, pady=(6, 0))
        value_bulk.columnconfigure(1, weight=1)
        value_bulk.columnconfigure(2, weight=1)
        ttk.Label(value_bulk, text="일괄 추가").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(value_bulk, textvariable=self.value_bulk_add_var).grid(
            row=0, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Button(value_bulk, text="적용", command=self._bulk_add_value_text).grid(
            row=0, column=2, padx=6, pady=4
        )
        ttk.Label(value_bulk, text="일괄 삭제").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(value_bulk, textvariable=self.value_bulk_remove_var).grid(
            row=1, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Button(value_bulk, text="적용", command=self._bulk_remove_value_text).grid(
            row=1, column=2, padx=6, pady=4
        )
        ttk.Label(value_bulk, text="정규식 패턴").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(value_bulk, textvariable=self.value_regex_pattern_var).grid(
            row=2, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Entry(value_bulk, textvariable=self.value_regex_replace_var).grid(
            row=2, column=2, sticky="we", padx=6, pady=4
        )
        ttk.Button(value_bulk, text="정규식 치환", command=self._bulk_regex_replace_value_text).grid(
            row=2, column=3, padx=6, pady=4
        )
        ttk.Label(value_bulk, text="행 필터 패턴").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(value_bulk, textvariable=self.value_filter_pattern_var).grid(
            row=3, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Button(value_bulk, text="일치만 유지", command=self._bulk_keep_values_by_regex).grid(
            row=3, column=2, padx=6, pady=4
        )
        ttk.Button(value_bulk, text="일치 삭제", command=self._bulk_delete_values_by_regex).grid(
            row=3, column=3, padx=6, pady=4
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

        tag_edit = ttk.Frame(tag_box)
        tag_edit.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(tag_edit, text="태그 검색 (자동완성)").pack(anchor="w")
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
        ttk.Button(tag_search_row, text="검색 선택", command=self._select_tags_by_query).grid(
            row=0, column=1, padx=(0, 4)
        )
        ttk.Button(tag_search_row, text="선택 반전", command=self._invert_tag_selection).grid(
            row=0, column=2
        )
        ttk.Label(
            tag_edit,
            text="태그 더블클릭으로 직접 수정",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(tag_edit, text="태그 입력 (쉼표 구분)").pack(anchor="w")
        ttk.Entry(tag_edit, textvariable=self.tag_input_var).pack(fill=tk.X, pady=(0, 6))

        tag_buttons = ttk.Frame(tag_edit)
        tag_buttons.pack(fill=tk.X)
        ttk.Button(tag_buttons, text="입력 태그 추가", command=self._append_tags).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(tag_buttons, text="입력 태그 삭제", command=self._remove_input_tags).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(tag_buttons, text="선택 태그 삭제", command=self._delete_selected_tags).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(tag_buttons, text="입력 초기화", command=self._clear_tag_input).pack(
            side=tk.LEFT
        )

        tag_bulk = ttk.Labelframe(tag_edit, text="태그 일괄 (현재 변수 전체)")
        tag_bulk.pack(fill=tk.X, pady=(6, 0))
        tag_bulk.columnconfigure(1, weight=1)
        tag_bulk.columnconfigure(2, weight=1)
        ttk.Label(tag_bulk, text="일괄 삽입").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(tag_bulk, textvariable=self.tag_bulk_add_var).grid(
            row=0, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Button(tag_bulk, text="적용", command=self._bulk_add_tags_to_values).grid(
            row=0, column=2, padx=6, pady=4
        )
        ttk.Label(tag_bulk, text="일괄 삭제").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(tag_bulk, textvariable=self.tag_bulk_remove_var).grid(
            row=1, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Button(tag_bulk, text="적용", command=self._bulk_remove_tags_from_values).grid(
            row=1, column=2, padx=6, pady=4
        )
        ttk.Label(tag_bulk, text="정규식 패턴").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(tag_bulk, textvariable=self.tag_regex_pattern_var).grid(
            row=2, column=1, sticky="we", padx=6, pady=4
        )
        ttk.Entry(tag_bulk, textvariable=self.tag_regex_replace_var).grid(
            row=2, column=2, sticky="we", padx=6, pady=4
        )
        ttk.Button(tag_bulk, text="정규식 치환", command=self._bulk_regex_replace_tags).grid(
            row=2, column=3, padx=6, pady=4
        )
        ttk.Button(tag_bulk, text="값 정규식 가져오기", command=self._copy_value_regex_to_tag_regex).grid(
            row=2, column=4, padx=6, pady=4
        )
        ttk.Label(tag_bulk, text="값 정규식으로 태그 교체").grid(
            row=3, column=0, sticky="w", padx=6, pady=4
        )
        ttk.Button(tag_bulk, text="선택 값 적용", command=self._replace_selected_tags_from_value_regex).grid(
            row=3, column=2, padx=6, pady=4
        )
        ttk.Button(
            tag_bulk,
            text="현재 변수 전체 적용",
            command=self._replace_variable_tags_from_value_regex,
        ).grid(row=3, column=3, padx=6, pady=4)
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
