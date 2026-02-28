from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from .file_utils import dedupe_keep_order
from .regex_service import extract_records_from_folder
from .tag_mapping_service import (
    apply_regex_to_rows,
    build_mapping_payload,
    build_tag_rows,
    build_variable_from_rows,
    reset_tags_to_values,
)
from .template_service import build_preset, save_preset


def _widget_is_descendant(widget: tk.Widget | None, ancestor: tk.Widget | None) -> bool:
    if widget is None or ancestor is None:
        return False
    cursor: tk.Widget | None = widget
    while cursor is not None:
        if cursor == ancestor:
            return True
        cursor = cursor.master
    return False


class FilenameValueExtractorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("파일명 패턴 추출기")
        self.root.geometry("1380x900")
        self.root.minsize(1120, 760)

        self.folder_var = tk.StringVar(value="")
        self.regex_var = tk.StringVar(value="")
        self.group_var = tk.StringVar(value="1")
        self.ignore_case_var = tk.BooleanVar(value=False)
        self.unique_var = tk.BooleanVar(value=True)
        self.sort_var = tk.BooleanVar(value=True)

        self.filter_ok_var = tk.BooleanVar(value=True)
        self.filter_no_match_var = tk.BooleanVar(value=True)
        self.filter_empty_var = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="대기")
        self.viewer_status_var = tk.StringVar(value="대기")
        self.viewer_load_var = tk.StringVar(value="로드: 0/0")
        self.tag_status_var = tk.StringVar(value="대기")
        self.tag_variable_name_var = tk.StringVar(value="character")
        self.tag_template_name_var = tk.StringVar(value="template")
        self.tag_regex_pattern_var = tk.StringVar(value="")
        self.tag_regex_replace_var = tk.StringVar(value="")
        self.tag_regex_source_var = tk.StringVar(value="현재 태그")
        self.tag_regex_ignore_case_var = tk.BooleanVar(value=False)

        self.notebook: ttk.Notebook | None = None
        self.extract_tab: ttk.Frame | None = None
        self.viewer_tab: ttk.Frame | None = None
        self.tag_tab: ttk.Frame | None = None

        self.value_listbox: tk.Listbox | None = None
        self.result_tree: ttk.Treeview | None = None
        self.viewer_canvas: tk.Canvas | None = None
        self.viewer_inner_frame: ttk.Frame | None = None
        self.viewer_window_id: int | None = None
        self.viewer_load_more_button: ttk.Button | None = None
        self.tag_tree: ttk.Treeview | None = None
        self.viewer_photos: list[ImageTk.PhotoImage] = []

        self.all_records: list[dict[str, str]] = []
        self.visible_records: list[dict[str, str]] = []
        self.values: list[str] = []
        self.tag_rows: list[dict[str, str]] = []
        self.last_extract_summary = "대기"

        self.viewer_mode = "none"
        self.viewer_value = ""
        self.viewer_file_path = ""
        self.viewer_records: list[dict[str, str]] = []
        self.viewer_title = ""
        self.viewer_loaded_count = 0
        self.viewer_batch_size = 40
        self.viewer_cols = 5

        self._build_ui()
        self._bind_mouse_wheel()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.extract_tab = ttk.Frame(self.notebook)
        self.viewer_tab = ttk.Frame(self.notebook)
        self.tag_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.extract_tab, text="추출")
        self.notebook.add(self.viewer_tab, text="이미지 뷰어")
        self.notebook.add(self.tag_tab, text="태그 생성")

        self._build_extract_tab(self.extract_tab)
        self._build_viewer_tab(self.viewer_tab)
        self._build_tag_tab(self.tag_tab)

    def _build_filter_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="상태 필터").pack(side=tk.LEFT)
        ttk.Checkbutton(
            parent,
            text="OK",
            variable=self.filter_ok_var,
            command=self._on_filter_changed,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Checkbutton(
            parent,
            text="NO_MATCH",
            variable=self.filter_no_match_var,
            command=self._on_filter_changed,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Checkbutton(
            parent,
            text="EMPTY",
            variable=self.filter_empty_var,
            command=self._on_filter_changed,
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _build_extract_tab(self, parent: ttk.Frame) -> None:
        control = ttk.Labelframe(parent, text="파일명 패턴 추출")
        control.pack(fill=tk.X, pady=(0, 8))
        control.columnconfigure(1, weight=1)

        ttk.Label(control, text="이미지 폴더").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.folder_var).grid(
            row=0,
            column=1,
            sticky="we",
            padx=6,
            pady=6,
        )
        ttk.Button(control, text="폴더 찾기", command=self._pick_folder).grid(
            row=0,
            column=2,
            padx=6,
            pady=6,
        )

        ttk.Label(control, text="정규식").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.regex_var).grid(
            row=1,
            column=1,
            sticky="we",
            padx=6,
            pady=6,
        )

        options = ttk.Frame(control)
        options.grid(row=1, column=2, sticky="e", padx=6, pady=6)
        ttk.Checkbutton(options, text="대소문자 무시", variable=self.ignore_case_var).pack(side=tk.LEFT)
        ttk.Checkbutton(options, text="중복 제거", variable=self.unique_var).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        ttk.Checkbutton(options, text="정렬", variable=self.sort_var).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(control, text="추출 그룹").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.group_var, width=12).grid(
            row=2,
            column=1,
            sticky="w",
            padx=6,
            pady=6,
        )
        ttk.Button(control, text="추출 실행", command=self._run_extract).grid(
            row=2,
            column=2,
            padx=6,
            pady=6,
        )

        ttk.Label(control, text="그룹 예시: 1, 2, name (비우면 전체 매치)").grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="w",
            padx=6,
            pady=(0, 6),
        )

        filter_row = ttk.Frame(parent)
        filter_row.pack(fill=tk.X, pady=(0, 8))
        self._build_filter_controls(filter_row)

        ttk.Label(parent, textvariable=self.status_var).pack(fill=tk.X, pady=(0, 8))

        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        value_frame = ttk.Labelframe(pane, text="값 리스트")
        self.value_listbox = tk.Listbox(value_frame, exportselection=False)
        self.value_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.value_listbox.bind("<<ListboxSelect>>", self._on_value_selected)
        self.value_listbox.bind("<Double-Button-1>", self._on_value_double_click)
        pane.add(value_frame, weight=1)

        result_frame = ttk.Labelframe(pane, text="파일별 결과")
        columns = ("file", "value", "status")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=20)
        self.result_tree.heading("file", text="파일명")
        self.result_tree.heading("value", text="추출값")
        self.result_tree.heading("status", text="상태")
        self.result_tree.column("file", width=430, anchor="w")
        self.result_tree.column("value", width=220, anchor="w")
        self.result_tree.column("status", width=90, anchor="center")
        yscroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=yscroll.set)
        self.result_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)
        self.result_tree.bind("<Double-Button-1>", self._on_tree_double_click)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)
        pane.add(result_frame, weight=2)

        action = ttk.Frame(parent)
        action.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(action, text="값 리스트 복사", command=self._copy_values).pack(side=tk.LEFT)
        ttk.Button(action, text="TXT 저장", command=self._save_values_txt).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(action, text="JSON 저장", command=self._save_values_json).pack(side=tk.LEFT, padx=(6, 0))

    def _build_viewer_tab(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(top, text="선택 값 썸네일 보기", command=self._show_from_selected_value).pack(side=tk.LEFT)
        ttk.Button(top, text="선택 파일 이미지 보기", command=self._show_from_selected_file).pack(
            side=tk.LEFT,
            padx=(6, 0),
        )
        ttk.Button(top, text="필터 반영 다시보기", command=self._refresh_current_view).pack(
            side=tk.LEFT,
            padx=(6, 0),
        )
        self.viewer_load_more_button = ttk.Button(top, text="더 불러오기", command=self._load_more_viewer_cards)
        self.viewer_load_more_button.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(top, textvariable=self.viewer_load_var).pack(side=tk.LEFT, padx=(10, 0))

        filter_row = ttk.Frame(parent)
        filter_row.pack(fill=tk.X, pady=(0, 8))
        self._build_filter_controls(filter_row)

        ttk.Label(parent, textvariable=self.viewer_status_var).pack(fill=tk.X, pady=(0, 8))

        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        self.viewer_canvas = tk.Canvas(frame, highlightthickness=0)
        yscroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.viewer_canvas.yview)
        self.viewer_canvas.configure(yscrollcommand=yscroll.set)
        self.viewer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.viewer_inner_frame = ttk.Frame(self.viewer_canvas)
        self.viewer_window_id = self.viewer_canvas.create_window((0, 0), window=self.viewer_inner_frame, anchor="nw")
        self.viewer_inner_frame.bind("<Configure>", self._on_viewer_inner_configure)
        self.viewer_canvas.bind("<Configure>", self._on_viewer_canvas_configure)
        self._render_records([], "표시할 이미지 없음")

    def _build_tag_tab(self, parent: ttk.Frame) -> None:
        control = ttk.Labelframe(parent, text="값 기반 태그 생성")
        control.pack(fill=tk.X, pady=(0, 8))
        control.columnconfigure(1, weight=1)
        control.columnconfigure(3, weight=1)
        control.columnconfigure(5, weight=1)

        ttk.Label(control, text="변수 이름").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.tag_variable_name_var, width=20).grid(
            row=0,
            column=1,
            sticky="we",
            padx=6,
            pady=6,
        )
        ttk.Label(control, text="템플릿 이름").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.tag_template_name_var, width=22).grid(
            row=0,
            column=3,
            sticky="we",
            padx=6,
            pady=6,
        )
        ttk.Button(control, text="현재 값 불러오기", command=self._load_tag_rows_from_values).grid(
            row=0,
            column=4,
            padx=6,
            pady=6,
            sticky="e",
        )
        ttk.Button(control, text="값 그대로 태그로", command=self._reset_tags_to_values).grid(
            row=0,
            column=5,
            padx=6,
            pady=6,
            sticky="w",
        )

        ttk.Label(control, text="치환 기준").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        source_combo = ttk.Combobox(
            control,
            textvariable=self.tag_regex_source_var,
            values=("현재 태그", "값"),
            state="readonly",
            width=16,
        )
        source_combo.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(control, text="정규식").grid(row=1, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.tag_regex_pattern_var).grid(
            row=1,
            column=3,
            sticky="we",
            padx=6,
            pady=6,
        )
        ttk.Label(control, text="치환식").grid(row=1, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(control, textvariable=self.tag_regex_replace_var).grid(
            row=1,
            column=5,
            sticky="we",
            padx=6,
            pady=6,
        )

        options = ttk.Frame(control)
        options.grid(row=2, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 6))
        ttk.Checkbutton(options, text="대소문자 무시", variable=self.tag_regex_ignore_case_var).pack(
            side=tk.LEFT
        )
        ttk.Button(options, text="일괄 정규식 치환 적용", command=self._apply_tag_regex).pack(
            side=tk.LEFT,
            padx=(10, 0),
        )
        ttk.Button(options, text="선택 항목 수정", command=self._edit_selected_tag).pack(
            side=tk.LEFT,
            padx=(6, 0),
        )
        ttk.Label(options, text="(태그 셀 더블클릭으로도 수정 가능)").pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(parent, textvariable=self.tag_status_var).pack(fill=tk.X, pady=(0, 8))

        preview = ttk.Labelframe(parent, text="값-태그 매핑")
        preview.pack(fill=tk.BOTH, expand=True)
        columns = ("value", "tag")
        self.tag_tree = ttk.Treeview(preview, columns=columns, show="headings")
        self.tag_tree.heading("value", text="값")
        self.tag_tree.heading("tag", text="태그 텍스트")
        self.tag_tree.column("value", width=340, anchor="w")
        self.tag_tree.column("tag", width=760, anchor="w")
        self.tag_tree.bind("<Double-Button-1>", self._on_tag_tree_double_click)
        yscroll = ttk.Scrollbar(preview, orient=tk.VERTICAL, command=self.tag_tree.yview)
        self.tag_tree.configure(yscrollcommand=yscroll.set)
        self.tag_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)

        action = ttk.Frame(parent)
        action.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(action, text="매핑 JSON 저장", command=self._save_tag_mapping_json).pack(side=tk.LEFT)
        ttk.Button(action, text="템플릿 JSON 저장", command=self._save_tag_template).pack(
            side=tk.LEFT,
            padx=(6, 0),
        )

    def _bind_mouse_wheel(self) -> None:
        self.root.bind_all("<MouseWheel>", self._on_global_mouse_wheel, add="+")
        self.root.bind_all("<Button-4>", self._on_global_mouse_wheel, add="+")
        self.root.bind_all("<Button-5>", self._on_global_mouse_wheel, add="+")

    def _viewer_is_active(self) -> bool:
        if self.notebook is None or self.viewer_tab is None:
            return False
        return self.notebook.select() == str(self.viewer_tab)

    def _pointer_over_viewer(self) -> bool:
        if self.viewer_canvas is None or self.viewer_inner_frame is None:
            return False
        x_root, y_root = self.root.winfo_pointerxy()
        widget = self.root.winfo_containing(x_root, y_root)
        return _widget_is_descendant(widget, self.viewer_canvas) or _widget_is_descendant(
            widget,
            self.viewer_inner_frame,
        )

    def _on_global_mouse_wheel(self, event: tk.Event) -> str | None:
        if not self._viewer_is_active():
            return None
        if not self._pointer_over_viewer():
            return None
        if self.viewer_canvas is None:
            return None

        steps = 0
        delta = int(getattr(event, "delta", 0) or 0)
        if delta != 0:
            steps = -int(delta / 120)
            if steps == 0:
                steps = -1 if delta > 0 else 1
        else:
            num = int(getattr(event, "num", 0) or 0)
            if num == 4:
                steps = -3
            elif num == 5:
                steps = 3

        if steps == 0:
            return None

        self.viewer_canvas.yview_scroll(steps, "units")
        self._maybe_load_more_viewer_cards()
        return "break"

    def _pick_folder(self) -> None:
        path = filedialog.askdirectory(title="이미지 폴더 선택")
        if path:
            self.folder_var.set(path)

    def _run_extract(self) -> None:
        folder = self.folder_var.get().strip()
        try:
            records, summary = extract_records_from_folder(
                folder,
                self.regex_var.get().strip(),
                self.group_var.get(),
                ignore_case=bool(self.ignore_case_var.get()),
            )
        except Exception as exc:
            messagebox.showerror("패턴 추출", str(exc))
            return

        self.all_records = records
        self.last_extract_summary = (
            f"완료: 파일 {summary['total']}개 | 매칭 {summary['matched']}개 | "
            f"미매칭 {summary['unmatched']}개 | 빈값 {summary['empty']}개"
        )
        self._refresh_lists_from_filters()
        self._refresh_current_view()

    def _selected_statuses(self) -> set[str]:
        statuses: set[str] = set()
        if self.filter_ok_var.get():
            statuses.add("OK")
        if self.filter_no_match_var.get():
            statuses.add("NO_MATCH")
        if self.filter_empty_var.get():
            statuses.add("EMPTY")
        return statuses

    def _refresh_lists_from_filters(self) -> None:
        statuses = self._selected_statuses()
        self.visible_records = [record for record in self.all_records if record["status"] in statuses]

        if self.result_tree:
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            for idx, record in enumerate(self.visible_records):
                self.result_tree.insert(
                    "",
                    tk.END,
                    iid=str(idx),
                    values=(record["file"], record["value"], record["status"]),
                )

        values = [record["value"] for record in self.visible_records if record["status"] == "OK" and record["value"]]
        if self.unique_var.get():
            values = dedupe_keep_order(values)
        if self.sort_var.get():
            values = sorted(values)
        self.values = values
        self._refresh_value_listbox(values)
        self.status_var.set(
            f"{self.last_extract_summary} | 필터 표시 {len(self.visible_records)}개 | 값 {len(values)}개"
        )

    def _on_filter_changed(self) -> None:
        self._refresh_lists_from_filters()
        self._refresh_current_view()

    def _refresh_value_listbox(self, values: list[str]) -> None:
        if not self.value_listbox:
            return
        self.value_listbox.delete(0, tk.END)
        for item in values:
            self.value_listbox.insert(tk.END, item)

    def _clear_results(self) -> None:
        self.all_records = []
        self.visible_records = []
        self.values = []
        self.tag_rows = []
        self.last_extract_summary = "대기"
        self._refresh_value_listbox([])
        self._refresh_tag_tree()
        self.tag_status_var.set("대기")
        if self.result_tree:
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
        self.viewer_mode = "none"
        self.viewer_value = ""
        self.viewer_file_path = ""
        self._render_records([], "표시할 이미지 없음")

    def _copy_values(self) -> None:
        if not self.values:
            messagebox.showwarning("값 리스트", "복사할 값이 없습니다.")
            return
        text = "\n".join(self.values)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set(f"값 리스트 복사 완료: {len(self.values)}개")

    def _save_values_txt(self) -> None:
        if not self.values:
            messagebox.showwarning("값 리스트", "저장할 값이 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="값 리스트 TXT 저장",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text("\n".join(self.values), encoding="utf-8")
            self.status_var.set(f"TXT 저장 완료: {path}")
        except Exception as exc:
            messagebox.showerror("값 리스트", f"TXT 저장 실패: {exc}")

    def _save_values_json(self) -> None:
        if not self.values:
            messagebox.showwarning("값 리스트", "저장할 값이 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="값 리스트 JSON 저장",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            payload = {"values": self.values}
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_var.set(f"JSON 저장 완료: {path}")
        except Exception as exc:
            messagebox.showerror("값 리스트", f"JSON 저장 실패: {exc}")

    def _selected_tree_record(self) -> dict[str, str] | None:
        if not self.result_tree:
            return None
        selected = self.result_tree.selection()
        if not selected:
            return None
        try:
            index = int(selected[0])
        except Exception:
            return None
        if index < 0 or index >= len(self.visible_records):
            return None
        return self.visible_records[index]

    def _selected_value(self) -> str:
        if not self.value_listbox:
            return ""
        selected = self.value_listbox.curselection()
        if not selected:
            return ""
        idx = int(selected[0])
        if idx < 0 or idx >= len(self.values):
            return ""
        return str(self.values[idx])

    def _show_from_selected_value(self, *, show_warning: bool = True) -> None:
        value = self._selected_value()
        if not value:
            if show_warning:
                messagebox.showwarning("이미지 뷰어", "값 리스트에서 항목을 선택하세요.")
            return
        records = [
            record
            for record in self.visible_records
            if record["status"] == "OK" and record["value"] == value
        ]
        self.viewer_mode = "value"
        self.viewer_value = value
        self.viewer_file_path = ""
        self._render_records(records, f"값 '{value}' 매칭 이미지: {len(records)}개")
        if self.notebook and self.viewer_tab:
            self.notebook.select(self.viewer_tab)

    def _show_from_selected_file(self, *, show_warning: bool = True) -> None:
        record = self._selected_tree_record()
        if record is None:
            if show_warning:
                messagebox.showwarning("이미지 뷰어", "파일별 결과에서 항목을 선택하세요.")
            return
        self.viewer_mode = "file"
        self.viewer_file_path = record["path"]
        self.viewer_value = ""
        self._render_records([record], f"파일 '{record['file']}'")
        if self.notebook and self.viewer_tab:
            self.notebook.select(self.viewer_tab)

    def _refresh_current_view(self) -> None:
        if self.viewer_mode == "value":
            records = [
                record
                for record in self.visible_records
                if record["status"] == "OK" and record["value"] == self.viewer_value
            ]
            self._render_records(records, f"값 '{self.viewer_value}' 매칭 이미지: {len(records)}개")
            return
        if self.viewer_mode == "file":
            records = [record for record in self.visible_records if record["path"] == self.viewer_file_path]
            if records:
                self._render_records(records, f"파일 '{records[0]['file']}'")
            else:
                self._render_records([], "필터로 인해 선택 파일이 숨겨졌습니다.")
            return
        self._render_records([], "표시할 이미지 없음")

    def _on_value_selected(self, _event: tk.Event) -> None:
        if not self._viewer_is_active():
            return
        self._show_from_selected_value(show_warning=False)

    def _on_tree_selected(self, _event: tk.Event) -> None:
        if not self._viewer_is_active():
            return
        self._show_from_selected_file(show_warning=False)

    def _on_value_double_click(self, _event: tk.Event) -> None:
        self._show_from_selected_value(show_warning=False)

    def _on_tree_double_click(self, _event: tk.Event) -> None:
        self._show_from_selected_file(show_warning=False)

    def _on_viewer_inner_configure(self, _event: tk.Event) -> None:
        if self.viewer_canvas:
            self.viewer_canvas.configure(scrollregion=self.viewer_canvas.bbox("all"))
        self._maybe_load_more_viewer_cards()

    def _on_viewer_canvas_configure(self, event: tk.Event) -> None:
        if self.viewer_canvas and self.viewer_window_id is not None:
            self.viewer_canvas.itemconfigure(self.viewer_window_id, width=int(event.width))
        self._maybe_load_more_viewer_cards()

    def _render_records(self, records: list[dict[str, str]], title: str) -> None:
        if not self.viewer_inner_frame:
            return
        for child in self.viewer_inner_frame.winfo_children():
            child.destroy()
        self.viewer_photos = []

        self.viewer_records = list(records)
        self.viewer_title = title
        self.viewer_loaded_count = 0
        self._update_viewer_load_ui()

        if not self.viewer_records:
            ttk.Label(self.viewer_inner_frame, text=title).grid(row=0, column=0, padx=12, pady=12)
            if self.viewer_canvas:
                self.viewer_canvas.yview_moveto(0.0)
            return

        self._load_more_viewer_cards()
        if self.viewer_canvas:
            self.viewer_canvas.yview_moveto(0.0)

    def _add_viewer_card(self, idx: int, record: dict[str, str]) -> None:
        if not self.viewer_inner_frame:
            return
        card = ttk.Frame(self.viewer_inner_frame, padding=8, relief=tk.GROOVE)
        row = idx // self.viewer_cols
        col = idx % self.viewer_cols
        card.grid(row=row, column=col, sticky="n", padx=8, pady=8)

        try:
            with Image.open(record["path"]) as image:
                preview = image.copy()
            preview.thumbnail((180, 180))
            photo = ImageTk.PhotoImage(preview)
            self.viewer_photos.append(photo)
            ttk.Label(card, image=photo).pack(anchor="center")
        except Exception:
            ttk.Label(card, text="이미지 로드 실패", width=24).pack(anchor="center", pady=6)

        ttk.Label(card, text=record["file"], wraplength=180).pack(anchor="w", pady=(6, 0))
        value_text = record["value"] if record["value"] else "-"
        ttk.Label(card, text=f"값: {value_text}", wraplength=180).pack(anchor="w")
        ttk.Label(card, text=f"상태: {record['status']}").pack(anchor="w")

    def _load_more_viewer_cards(self) -> None:
        if not self.viewer_records:
            self._update_viewer_load_ui()
            return
        if self.viewer_loaded_count >= len(self.viewer_records):
            self._update_viewer_load_ui()
            return

        start = self.viewer_loaded_count
        end = min(start + self.viewer_batch_size, len(self.viewer_records))
        for idx in range(start, end):
            self._add_viewer_card(idx, self.viewer_records[idx])
        self.viewer_loaded_count = end

        if self.viewer_canvas:
            self.viewer_canvas.update_idletasks()
            self.viewer_canvas.configure(scrollregion=self.viewer_canvas.bbox("all"))
        self._update_viewer_load_ui()

    def _maybe_load_more_viewer_cards(self) -> None:
        if self.viewer_canvas is None:
            return
        if not self.viewer_records:
            return
        if self.viewer_loaded_count >= len(self.viewer_records):
            return
        _top, bottom = self.viewer_canvas.yview()
        if bottom >= 0.92:
            self._load_more_viewer_cards()

    def _update_viewer_load_ui(self) -> None:
        total = len(self.viewer_records)
        loaded = self.viewer_loaded_count
        self.viewer_load_var.set(f"로드: {loaded}/{total}")
        self.viewer_status_var.set(
            f"{self.viewer_title} | 로드 {loaded}/{total}" if self.viewer_title else "대기"
        )
        if self.viewer_load_more_button:
            self.viewer_load_more_button.configure(state=(tk.NORMAL if loaded < total else tk.DISABLED))

    def _load_tag_rows_from_values(self) -> None:
        if not self.values:
            messagebox.showwarning("태그 생성", "먼저 추출 탭에서 값을 만들어 주세요.")
            return
        self.tag_rows = build_tag_rows(self.values)
        self._refresh_tag_tree()
        self.tag_status_var.set(f"값 {len(self.tag_rows)}개를 태그 편집 목록으로 불러왔습니다.")

    def _refresh_tag_tree(self) -> None:
        if self.tag_tree is None:
            return
        for item in self.tag_tree.get_children():
            self.tag_tree.delete(item)
        for idx, row in enumerate(self.tag_rows):
            self.tag_tree.insert("", tk.END, iid=str(idx), values=(row["value"], row["tag"]))

    def _selected_tag_row_index(self) -> int | None:
        if self.tag_tree is None:
            return None
        selected = self.tag_tree.selection()
        if not selected:
            return None
        try:
            idx = int(selected[0])
        except Exception:
            return None
        if idx < 0 or idx >= len(self.tag_rows):
            return None
        return idx

    def _edit_selected_tag(self, *, row_index: int | None = None) -> None:
        idx = row_index if row_index is not None else self._selected_tag_row_index()
        if idx is None:
            messagebox.showwarning("태그 생성", "수정할 항목을 선택하세요.")
            return

        row = self.tag_rows[idx]
        edited = simpledialog.askstring(
            "태그 수정",
            f"값: {row['value']}\n태그 텍스트를 입력하세요. (쉼표로 여러 태그 구분)",
            initialvalue=row["tag"],
            parent=self.root,
        )
        if edited is None:
            return
        row["tag"] = edited.strip()
        self._refresh_tag_tree()
        if self.tag_tree:
            self.tag_tree.selection_set(str(idx))
            self.tag_tree.focus(str(idx))
        self.tag_status_var.set(f"'{row['value']}' 태그를 수정했습니다.")

    def _on_tag_tree_double_click(self, event: tk.Event) -> None:
        if self.tag_tree is None:
            return
        row_id = self.tag_tree.identify_row(event.y)
        if not row_id:
            return
        self.tag_tree.selection_set(row_id)
        self.tag_tree.focus(row_id)
        try:
            idx = int(row_id)
        except Exception:
            return
        self._edit_selected_tag(row_index=idx)

    def _reset_tags_to_values(self) -> None:
        if not self.tag_rows:
            messagebox.showwarning("태그 생성", "먼저 값을 불러와 주세요.")
            return
        reset_tags_to_values(self.tag_rows)
        self._refresh_tag_tree()
        self.tag_status_var.set("모든 태그를 원본 값으로 초기화했습니다.")

    def _apply_tag_regex(self) -> None:
        if not self.tag_rows:
            messagebox.showwarning("태그 생성", "먼저 값을 불러와 주세요.")
            return

        source = "value" if self.tag_regex_source_var.get() == "값" else "tag"
        try:
            changed = apply_regex_to_rows(
                self.tag_rows,
                self.tag_regex_pattern_var.get(),
                self.tag_regex_replace_var.get(),
                ignore_case=bool(self.tag_regex_ignore_case_var.get()),
                source=source,
            )
        except Exception as exc:
            messagebox.showerror("태그 생성", str(exc))
            return

        self._refresh_tag_tree()
        source_label = "값" if source == "value" else "현재 태그"
        self.tag_status_var.set(
            f"일괄 치환 완료: {len(self.tag_rows)}개 처리, 변경 {changed}개 (기준: {source_label})"
        )

    def _save_tag_mapping_json(self) -> None:
        if not self.tag_rows:
            messagebox.showwarning("태그 생성", "저장할 값/태그 매핑이 없습니다.")
            return

        template_name = self.tag_template_name_var.get().strip() or "template"
        path = filedialog.asksaveasfilename(
            title="값-태그 매핑 저장",
            defaultextension=".json",
            initialfile=f"{template_name}_mapping.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        payload = build_mapping_payload(
            template_name=template_name,
            variable_name=self.tag_variable_name_var.get(),
            rows=self.tag_rows,
        )
        try:
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.tag_status_var.set(f"매핑 JSON 저장 완료: {path}")
        except Exception as exc:
            messagebox.showerror("태그 생성", f"저장 실패: {exc}")
            self.tag_status_var.set(f"저장 실패: {exc}")

    def _save_tag_template(self) -> None:
        if not self.tag_rows:
            messagebox.showwarning("태그 생성", "저장할 값/태그 매핑이 없습니다.")
            return

        try:
            variable = build_variable_from_rows(self.tag_variable_name_var.get(), self.tag_rows)
        except Exception as exc:
            messagebox.showerror("태그 생성", str(exc))
            return

        template_name = self.tag_template_name_var.get().strip() or "template"
        preset = build_preset(template_name, variable)

        templates_dir = Path("templates")
        templates_dir.mkdir(parents=True, exist_ok=True)
        initial_name = f"{template_name}.json"
        path = filedialog.asksaveasfilename(
            title="템플릿 저장",
            defaultextension=".json",
            initialdir=str(templates_dir.resolve()),
            initialfile=initial_name,
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            confirmoverwrite=True,
        )
        if not path:
            return

        try:
            save_preset(path, preset)
            self.tag_status_var.set(f"템플릿 저장 완료: {path}")
        except Exception as exc:
            messagebox.showerror("태그 생성", f"저장 실패: {exc}")
            self.tag_status_var.set(f"저장 실패: {exc}")
