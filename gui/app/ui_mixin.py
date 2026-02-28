from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..result_panel import ResultPanel
from ..template_editor import TemplateEditorPanel


class AppUiMixin:
    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.root, width=240)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)

        content = ttk.Frame(self.root)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="EXIF Template Tool", font=("맑은 고딕", 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(16, 4)
        )

        nav = ttk.Frame(sidebar)
        nav.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        nav.columnconfigure(0, weight=1)

        for idx, (tab_id, label) in enumerate(
            [
                ("template", "템플릿"),
                ("search", "검색"),
                ("rename", "파일명 변경"),
                ("move", "분류(이동)"),
                ("log", "로그"),
            ]
        ):
            btn = ttk.Button(nav, text=label, command=lambda key=tab_id: self._show_tab(key))
            btn.grid(row=idx, column=0, sticky="ew", pady=3)
            self.nav_buttons[tab_id] = btn

        progress = ttk.Labelframe(sidebar, text="작업 상태")
        progress.grid(row=2, column=0, sticky="ew", padx=10, pady=(6, 10))
        progress.columnconfigure(0, weight=1)
        ttk.Label(progress, textvariable=self.sidebar_job_var).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 6)
        )
        ttk.Button(progress, text="작업 취소", command=self._cancel_worker).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        template_tab = ttk.Frame(content)
        search_tab = ttk.Frame(content)
        rename_tab = ttk.Frame(content)
        move_tab = ttk.Frame(content)
        log_tab = ttk.Frame(content)

        self.tab_frames = {
            "template": template_tab,
            "search": search_tab,
            "rename": rename_tab,
            "move": move_tab,
            "log": log_tab,
        }

        for frame in self.tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self._build_template_tab(template_tab)
        self._build_search_tab(search_tab)
        self._build_rename_tab(rename_tab)
        self._build_move_tab(move_tab)
        self._build_log_tab(log_tab)
        self._show_tab("template")

    def _build_template_tab(self, parent: ttk.Frame) -> None:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        top = ttk.Labelframe(wrapper, text="템플릿 관리")
        top.pack(fill=tk.X, padx=0, pady=(0, 8))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="템플릿 파일").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(top, textvariable=self.template_path_var, state="readonly").grid(
            row=0, column=1, sticky="we", padx=6, pady=6
        )
        load_button = ttk.Menubutton(top, text="불러오기")
        load_menu = tk.Menu(load_button, tearoff=0)
        load_menu.add_command(label="초기화 불러오기", command=self._load_template_reset)
        load_menu.add_command(label="변수 추가 불러오기", command=self._load_template_add_variables)
        load_button.configure(menu=load_menu)
        load_button.grid(row=0, column=2, padx=6, pady=6)
        self.template_load_menu_button = load_button
        self.template_load_menu = load_menu
        ttk.Button(top, text="저장", command=self._save_template).grid(
            row=0, column=3, padx=6, pady=6
        )
        ttk.Button(top, text="유효성 검증", command=self._validate_template).grid(
            row=0, column=4, padx=6, pady=6
        )

        build_frame = ttk.Labelframe(wrapper, text="변수 생성 (폴더/SDSTUDIO,NAIS2 프리셋)")
        build_frame.pack(fill=tk.X, padx=0, pady=8)
        build_frame.columnconfigure(1, weight=1)
        ttk.Label(build_frame, text="이미지 폴더").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(build_frame, textvariable=self.build_folder_var).grid(
            row=0, column=1, sticky="we", padx=6, pady=6
        )
        ttk.Button(build_frame, text="찾기", command=self._pick_build_folder).grid(
            row=0, column=2, padx=6, pady=6
        )
        ttk.Button(build_frame, text="폴더로 생성", command=self._build_variable).grid(
            row=0, column=3, padx=6, pady=6
        )

        ttk.Label(build_frame, text="프리셋 JSON").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(build_frame, textvariable=self.build_preset_json_var).grid(
            row=1, column=1, sticky="we", padx=6, pady=6
        )
        ttk.Button(build_frame, text="찾기", command=self._pick_build_preset_json).grid(
            row=1, column=2, padx=6, pady=6
        )
        ttk.Button(build_frame, text="JSON으로 생성", command=self._build_variable_from_json).grid(
            row=1, column=3, padx=6, pady=6
        )

        ttk.Checkbutton(
            build_frame,
            text="네거티브 태그 포함",
            variable=self.build_include_negative_var,
        ).grid(row=2, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(wrapper, textvariable=self.template_status_var).pack(
            fill=tk.X, padx=6, pady=(4, 8), anchor="w"
        )

        editor_frame = ttk.Labelframe(wrapper, text="템플릿 편집 UI")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.template_editor = TemplateEditorPanel(
            editor_frame,
            get_preset=self._get_preset,
            set_preset=self._set_preset,
            set_status=self.template_status_var.set,
            on_changed=self._refresh_template_ui,
        )

    def _build_search_tab(self, parent: ttk.Frame) -> None:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ctrl = ttk.Labelframe(wrapper, text="검색")
        ctrl.pack(fill=tk.X, padx=0, pady=(0, 8))

        folder_row = ttk.Frame(ctrl)
        folder_row.pack(fill=tk.X, padx=6, pady=(6, 3))
        folder_row.columnconfigure(1, weight=1)
        ttk.Label(folder_row, text="작업 폴더").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(folder_row, textvariable=self.search_folder_var).grid(
            row=0, column=1, sticky="we", padx=0, pady=0
        )
        ttk.Button(folder_row, text="찾기", command=self._pick_search_folder).grid(
            row=0, column=2, padx=(8, 0), pady=0
        )

        query_row = ttk.Frame(ctrl)
        query_row.pack(fill=tk.X, padx=6, pady=3)
        query_row.columnconfigure(1, weight=1)
        ttk.Label(query_row, text="검색 태그").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(query_row, textvariable=self.search_tags_var).grid(
            row=0, column=1, sticky="we", padx=0, pady=0
        )
        ttk.Checkbutton(
            query_row,
            text="네거티브 태그 포함",
            variable=self.search_include_negative_var,
        ).grid(row=0, column=2, sticky="w", padx=(8, 0), pady=0)

        bottom_row = ttk.Frame(ctrl)
        bottom_row.pack(fill=tk.X, padx=6, pady=(3, 6))
        bottom_row.columnconfigure(0, weight=1)

        ttk.Label(bottom_row, textvariable=self.search_status_var).grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )

        actions = ttk.Frame(bottom_row)
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="검색 실행", command=self._run_search).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="취소", command=self._cancel_worker).pack(side=tk.LEFT)

        result_frame = ttk.Labelframe(wrapper, text="검색 결과")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.search_result_panel = ResultPanel(
            result_frame,
            list_ratio=0.23,
            status_filters=("OK", "ERROR"),
        )

    def _build_rename_tab(self, parent: ttk.Frame) -> None:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ctrl = ttk.Labelframe(wrapper, text="템플릿 기반 파일명 변경")
        ctrl.pack(fill=tk.X, padx=0, pady=(0, 8))

        folder_row = ttk.Frame(ctrl)
        folder_row.pack(fill=tk.X, padx=6, pady=(6, 3))
        folder_row.columnconfigure(1, weight=1)
        ttk.Label(folder_row, text="작업 폴더").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(folder_row, textvariable=self.rename_folder_var).grid(
            row=0, column=1, sticky="we", padx=0, pady=0
        )
        ttk.Button(folder_row, text="찾기", command=self._pick_rename_folder).grid(
            row=0, column=2, padx=(8, 0), pady=0
        )

        preset_row = ttk.Frame(ctrl)
        preset_row.pack(fill=tk.X, padx=6, pady=3)
        preset_row.columnconfigure(1, weight=1)
        ttk.Label(preset_row, text="사용 템플릿").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.rename_template_combo = ttk.Combobox(
            preset_row,
            textvariable=self.rename_template_file_var,
            state="readonly",
        )
        self.rename_template_combo.grid(row=0, column=1, sticky="we", padx=0, pady=0)
        ttk.Button(
            preset_row,
            text="새로고침",
            command=self._refresh_task_template_choices,
        ).grid(row=0, column=2, padx=(8, 0), pady=0)

        order_row = ttk.Frame(ctrl)
        order_row.pack(fill=tk.X, padx=6, pady=3)
        order_row.columnconfigure(1, weight=1)
        ttk.Label(order_row, text="변수 순서").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(order_row, textvariable=self.rename_order_var).grid(
            row=0, column=1, sticky="we", padx=0, pady=0
        )
        ttk.Button(order_row, text="템플릿 순서 채우기", command=self._fill_rename_order).grid(
            row=0, column=2, padx=(8, 0), pady=0
        )

        bottom_row = ttk.Frame(ctrl)
        bottom_row.pack(fill=tk.X, padx=6, pady=(3, 6))
        bottom_row.columnconfigure(1, weight=1)

        options = ttk.Frame(bottom_row)
        options.grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="드라이런", variable=self.rename_dry_run_var).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Checkbutton(options, text="접두사 모드", variable=self.rename_prefix_var).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Checkbutton(
            options, text="네거티브 태그 포함", variable=self.rename_include_negative_var
        ).pack(side=tk.LEFT)

        ttk.Label(bottom_row, textvariable=self.rename_status_var).grid(
            row=0, column=1, sticky="e", padx=(10, 10)
        )

        actions = ttk.Frame(bottom_row)
        actions.grid(row=0, column=2, sticky="e")
        ttk.Button(actions, text="변경 실행", command=self._run_rename).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="로그 보기", command=lambda: self._open_task_log("rename")).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="초기화", command=self._reset_rename_form).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="취소", command=self._cancel_worker).pack(side=tk.LEFT)

        result_frame = ttk.Labelframe(wrapper, text="변경 결과")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.rename_result_panel = ResultPanel(result_frame, list_ratio=0.23)

    def _build_move_tab(self, parent: ttk.Frame) -> None:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ctrl = ttk.Labelframe(wrapper, text="템플릿 기반 분류(이동)")
        ctrl.pack(fill=tk.X, padx=0, pady=(0, 8))

        folder_row = ttk.Frame(ctrl)
        folder_row.pack(fill=tk.X, padx=6, pady=(6, 3))
        folder_row.columnconfigure(1, weight=1)

        ttk.Label(folder_row, text="작업 폴더").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(folder_row, textvariable=self.move_source_var).grid(
            row=0, column=1, sticky="we", padx=0, pady=0
        )
        ttk.Button(folder_row, text="찾기", command=self._pick_move_source).grid(
            row=0, column=2, padx=(8, 0), pady=0
        )

        preset_row = ttk.Frame(ctrl)
        preset_row.pack(fill=tk.X, padx=6, pady=3)
        preset_row.columnconfigure(1, weight=1)
        ttk.Label(preset_row, text="사용 템플릿").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.move_template_combo = ttk.Combobox(
            preset_row,
            textvariable=self.move_template_file_var,
            state="readonly",
        )
        self.move_template_combo.grid(row=0, column=1, sticky="we", padx=0, pady=0)
        ttk.Button(
            preset_row,
            text="새로고침",
            command=self._refresh_task_template_choices,
        ).grid(row=0, column=2, padx=(8, 0), pady=0)

        variable_row = ttk.Frame(ctrl)
        variable_row.pack(fill=tk.X, padx=6, pady=3)
        variable_row.columnconfigure(1, weight=1)

        ttk.Label(variable_row, text="분류 변수 순서").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Entry(variable_row, textvariable=self.move_order_var).grid(
            row=0, column=1, sticky="we", padx=0, pady=0
        )
        ttk.Button(variable_row, text="순서 채우기", command=self._fill_move_order).grid(
            row=0, column=2, padx=(8, 12), pady=0
        )

        bottom_row = ttk.Frame(ctrl)
        bottom_row.pack(fill=tk.X, padx=6, pady=(3, 6))
        bottom_row.columnconfigure(1, weight=1)

        options = ttk.Frame(bottom_row)
        options.grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="드라이런", variable=self.move_dry_run_var).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Checkbutton(
            options, text="네거티브 태그 포함", variable=self.move_include_negative_var
        ).pack(side=tk.LEFT)

        ttk.Label(bottom_row, textvariable=self.move_status_var).grid(
            row=0, column=1, sticky="e", padx=(10, 10)
        )

        actions = ttk.Frame(bottom_row)
        actions.grid(row=0, column=2, sticky="e")
        ttk.Button(actions, text="분류 실행", command=self._run_move).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="로그 보기", command=lambda: self._open_task_log("move")).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="초기화", command=self._reset_move_form).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(actions, text="취소", command=self._cancel_worker).pack(side=tk.LEFT)

        result_frame = ttk.Labelframe(wrapper, text="분류 결과")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.move_result_panel = ResultPanel(result_frame, list_ratio=0.23)

    def _build_log_tab(self, parent: ttk.Frame) -> None:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        notebook = ttk.Notebook(wrapper)
        notebook.pack(fill=tk.BOTH, expand=True)
        self.log_notebook = notebook

        base_frame = ttk.Frame(notebook)
        rename_frame = ttk.Frame(notebook)
        move_frame = ttk.Frame(notebook)
        self.rename_log_tab_frame = rename_frame
        self.move_log_tab_frame = move_frame
        notebook.add(base_frame, text="기본 로그")
        notebook.add(rename_frame, text="파일명 변경 로그")
        notebook.add(move_frame, text="분류 로그")

        base_box = ttk.Labelframe(base_frame, text="기본 로그")
        base_box.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.log_text = tk.Text(base_box, wrap="word")
        base_scroll = ttk.Scrollbar(base_box, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=base_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        base_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

        rename_box = ttk.Labelframe(rename_frame, text="파일명 변경 결과 로그")
        rename_box.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        ttk.Label(rename_box, textvariable=self.rename_log_summary_var).pack(
            fill=tk.X, padx=8, pady=(8, 4)
        )
        rename_filter_row = ttk.Frame(rename_box)
        rename_filter_row.pack(fill=tk.X, padx=8, pady=(0, 4))
        ttk.Label(rename_filter_row, text="상태 필터").pack(side=tk.LEFT, padx=(0, 8))
        for status in ("OK", "UNKNOWN", "CONFLICT", "ERROR"):
            ttk.Checkbutton(
                rename_filter_row,
                text=status,
                variable=self.rename_log_filter_vars[status],
                command=self._refresh_rename_log_tree,
            ).pack(side=tk.LEFT, padx=4)
        rename_table_wrap = ttk.Frame(rename_box)
        rename_table_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        rename_table_wrap.rowconfigure(0, weight=1)
        rename_table_wrap.columnconfigure(0, weight=1)
        self.rename_log_tree = ttk.Treeview(
            rename_table_wrap,
            columns=("status", "before", "after", "detail"),
            show="headings",
        )
        self.rename_log_tree.heading("status", text="상태")
        self.rename_log_tree.heading("before", text="변경 전")
        self.rename_log_tree.heading("after", text="변경 후")
        self.rename_log_tree.heading("detail", text="상세")
        self.rename_log_tree.column("status", width=90, anchor="center", stretch=False)
        self.rename_log_tree.column("before", width=380, anchor="w")
        self.rename_log_tree.column("after", width=380, anchor="w")
        self.rename_log_tree.column("detail", width=360, anchor="w")
        rename_v_scroll = ttk.Scrollbar(
            rename_table_wrap, orient=tk.VERTICAL, command=self.rename_log_tree.yview
        )
        rename_h_scroll = ttk.Scrollbar(
            rename_table_wrap, orient=tk.HORIZONTAL, command=self.rename_log_tree.xview
        )
        self.rename_log_tree.configure(
            yscrollcommand=rename_v_scroll.set,
            xscrollcommand=rename_h_scroll.set,
        )
        self.rename_log_tree.grid(row=0, column=0, sticky="nsew")
        rename_v_scroll.grid(row=0, column=1, sticky="ns")
        rename_h_scroll.grid(row=1, column=0, sticky="ew")
        self.rename_log_tree.tag_configure("OK", foreground="#2e7d32")
        self.rename_log_tree.tag_configure("UNKNOWN", foreground="#f57f17")
        self.rename_log_tree.tag_configure("CONFLICT", foreground="#c62828")
        self.rename_log_tree.tag_configure("ERROR", foreground="#b71c1c")

        move_box = ttk.Labelframe(move_frame, text="분류 결과 로그")
        move_box.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        ttk.Label(move_box, textvariable=self.move_log_summary_var).pack(
            fill=tk.X, padx=8, pady=(8, 4)
        )
        move_filter_row = ttk.Frame(move_box)
        move_filter_row.pack(fill=tk.X, padx=8, pady=(0, 4))
        ttk.Label(move_filter_row, text="상태 필터").pack(side=tk.LEFT, padx=(0, 8))
        for status in ("OK", "UNKNOWN", "CONFLICT", "ERROR"):
            ttk.Checkbutton(
                move_filter_row,
                text=status,
                variable=self.move_log_filter_vars[status],
                command=self._refresh_move_log_tree,
            ).pack(side=tk.LEFT, padx=4)
        move_table_wrap = ttk.Frame(move_box)
        move_table_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        move_table_wrap.rowconfigure(0, weight=1)
        move_table_wrap.columnconfigure(0, weight=1)
        self.move_log_tree = ttk.Treeview(
            move_table_wrap,
            columns=("status", "before", "after", "detail"),
            show="headings",
        )
        self.move_log_tree.heading("status", text="상태")
        self.move_log_tree.heading("before", text="변경 전")
        self.move_log_tree.heading("after", text="변경 후")
        self.move_log_tree.heading("detail", text="상세")
        self.move_log_tree.column("status", width=90, anchor="center", stretch=False)
        self.move_log_tree.column("before", width=380, anchor="w")
        self.move_log_tree.column("after", width=380, anchor="w")
        self.move_log_tree.column("detail", width=360, anchor="w")
        move_v_scroll = ttk.Scrollbar(
            move_table_wrap, orient=tk.VERTICAL, command=self.move_log_tree.yview
        )
        move_h_scroll = ttk.Scrollbar(
            move_table_wrap, orient=tk.HORIZONTAL, command=self.move_log_tree.xview
        )
        self.move_log_tree.configure(
            yscrollcommand=move_v_scroll.set,
            xscrollcommand=move_h_scroll.set,
        )
        self.move_log_tree.grid(row=0, column=0, sticky="nsew")
        move_v_scroll.grid(row=0, column=1, sticky="ns")
        move_h_scroll.grid(row=1, column=0, sticky="ew")
        self.move_log_tree.tag_configure("OK", foreground="#2e7d32")
        self.move_log_tree.tag_configure("UNKNOWN", foreground="#f57f17")
        self.move_log_tree.tag_configure("CONFLICT", foreground="#c62828")
        self.move_log_tree.tag_configure("ERROR", foreground="#b71c1c")

    def _show_tab(self, tab_id: str) -> None:
        frame = self.tab_frames.get(tab_id)
        if not frame:
            return
        self.active_tab = tab_id
        frame.tkraise()
        for key, button in self.nav_buttons.items():
            if key == tab_id:
                button.state(["disabled"])
            else:
                button.state(["!disabled"])
