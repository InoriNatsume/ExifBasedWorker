from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

try:
    from tools.hash_verification.fingerprint_compare_core import (
        ALL_STATUSES,
        STATUS_FINGERPRINT_NOT_FOUND,
        STATUS_MATCH,
        STATUS_NAME_MISMATCH,
        STATUS_READ_ERROR,
        STATUS_SOURCE_DUPLICATE,
        CompareRecord,
        CompareWorker,
        FileEntry,
    )
except ModuleNotFoundError:
    # 파일 직접 실행(`python tools\\hash_verification\\compare_by_fingerprint_ui.py`) 경로 호환
    from fingerprint_compare_core import (  # type: ignore
        ALL_STATUSES,
        STATUS_FINGERPRINT_NOT_FOUND,
        STATUS_MATCH,
        STATUS_NAME_MISMATCH,
        STATUS_READ_ERROR,
        STATUS_SOURCE_DUPLICATE,
        CompareRecord,
        CompareWorker,
        FileEntry,
    )


class FingerprintCompareApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("해시 기반 파일명 검증 도구")
        self.root.geometry("1800x980")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._closing = False

        self.queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: CompareWorker | None = None

        self.records: list[CompareRecord] = []
        self.filtered_records: list[CompareRecord] = []
        self.issue_records: list[CompareRecord] = []
        self.source_entries_by_path: dict[str, FileEntry] = {}
        self.source_duplicates: dict[str, list[FileEntry]] = {}
        self._image_cache: dict[tuple[str, int, int], ImageTk.PhotoImage] = {}
        self._image_cache_order: list[tuple[str, int, int]] = []
        self._image_cache_limit = 120

        self.source_dir_var = tk.StringVar()
        self.result_dir_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="hash")
        self.workers_var = tk.IntVar(value=max(1, min(8, os.cpu_count() or 1)))
        self.progress_var = tk.StringVar(value="대기")

        self.result_filter_vars: dict[str, tk.BooleanVar] = {
            STATUS_MATCH: tk.BooleanVar(value=True),
            STATUS_NAME_MISMATCH: tk.BooleanVar(value=True),
            STATUS_FINGERPRINT_NOT_FOUND: tk.BooleanVar(value=True),
            STATUS_SOURCE_DUPLICATE: tk.BooleanVar(value=True),
            STATUS_READ_ERROR: tk.BooleanVar(value=True),
        }

        self._build_layout()
        self._poll_queue()

    def _build_layout(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="원본 폴더").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.source_dir_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 6)
        )
        ttk.Button(top, text="찾기", command=self._pick_source_dir).grid(row=0, column=2, padx=4)

        ttk.Label(top, text="결과 폴더").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.result_dir_var).grid(
            row=1, column=1, sticky="ew", padx=(8, 6), pady=(8, 0)
        )
        ttk.Button(top, text="찾기", command=self._pick_result_dir).grid(row=1, column=2, padx=4, pady=(8, 0))

        ttk.Label(top, text="지문 방식").grid(row=0, column=3, sticky="w", padx=(16, 0))
        self.mode_combo = ttk.Combobox(
            top,
            values=["hash", "dhash"],
            textvariable=self.mode_var,
            width=10,
            state="readonly",
        )
        self.mode_combo.grid(row=0, column=4, sticky="w", padx=(6, 10))

        ttk.Label(top, text="프로세스").grid(row=0, column=5, sticky="w")
        self.worker_spin = ttk.Spinbox(top, from_=1, to=max(1, os.cpu_count() or 1), textvariable=self.workers_var, width=6)
        self.worker_spin.grid(row=0, column=6, sticky="w", padx=(6, 12))

        self.run_button = ttk.Button(top, text="비교 실행", command=self._start_compare)
        self.run_button.grid(row=0, column=7, padx=(0, 6))

        self.cancel_button = ttk.Button(top, text="중지", command=self._cancel_compare, state="disabled")
        self.cancel_button.grid(row=0, column=8)

        ttk.Label(top, textvariable=self.progress_var).grid(
            row=1, column=3, columnspan=6, sticky="w", padx=(16, 0), pady=(8, 0)
        )

        top.columnconfigure(1, weight=1)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.result_tab = ttk.Frame(self.notebook)
        self.issue_tab = ttk.Frame(self.notebook)
        self.dup_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.result_tab, text="결과")
        self.notebook.add(self.issue_tab, text="문제아")
        self.notebook.add(self.dup_tab, text="원본 중복")

        self._build_result_tab()
        self._build_issue_tab()
        self._build_duplicate_tab()

    def _build_result_tab(self) -> None:
        top = ttk.Frame(self.result_tab, padding=8)
        top.pack(fill=tk.X)

        self.summary_text = tk.Text(top, height=5, wrap="word")
        self.summary_text.pack(fill=tk.X)
        self.summary_text.insert("1.0", "아직 실행 전입니다.")
        self.summary_text.configure(state="disabled")

        filter_frame = ttk.LabelFrame(self.result_tab, text="상태 필터", padding=8)
        filter_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        col = 0
        for status in ALL_STATUSES:
            ttk.Checkbutton(
                filter_frame,
                text=status,
                variable=self.result_filter_vars[status],
                command=self._refresh_result_view,
            ).grid(row=0, column=col, sticky="w", padx=(0, 10))
            col += 1

        list_frame = ttk.Frame(self.result_tab, padding=(8, 0, 8, 8))
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("status", "result_name", "source_info", "detail")
        self.result_tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.result_tree.heading("status", text="상태")
        self.result_tree.heading("result_name", text="결과 파일명")
        self.result_tree.heading("source_info", text="원본 후보")
        self.result_tree.heading("detail", text="상세")
        self.result_tree.column("status", width=170, anchor="center")
        self.result_tree.column("result_name", width=360, anchor="w")
        self.result_tree.column("source_info", width=320, anchor="w")
        self.result_tree.column("detail", width=760, anchor="w")

        yscroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        xscroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_tree_select)

    def _build_issue_tab(self) -> None:
        top = ttk.Frame(self.issue_tab, padding=8)
        top.pack(fill=tk.X)

        self.prev_issue_button = ttk.Button(top, text="이전", command=self._select_prev_issue)
        self.prev_issue_button.pack(side=tk.LEFT)
        self.next_issue_button = ttk.Button(top, text="다음", command=self._select_next_issue)
        self.next_issue_button.pack(side=tk.LEFT, padx=(6, 0))
        self.issue_index_label = ttk.Label(top, text="0 / 0")
        self.issue_index_label.pack(side=tk.LEFT, padx=(12, 0))

        body = ttk.Panedwindow(self.issue_tab, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)

        issue_cols = ("status", "result_name", "detail")
        self.issue_tree = ttk.Treeview(left, columns=issue_cols, show="headings")
        self.issue_tree.heading("status", text="상태")
        self.issue_tree.heading("result_name", text="결과 파일명")
        self.issue_tree.heading("detail", text="상세")
        self.issue_tree.column("status", width=150, anchor="center")
        self.issue_tree.column("result_name", width=280, anchor="w")
        self.issue_tree.column("detail", width=320, anchor="w")
        issue_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.issue_tree.yview)
        self.issue_tree.configure(yscrollcommand=issue_scroll.set)
        self.issue_tree.grid(row=0, column=0, sticky="nsew")
        issue_scroll.grid(row=0, column=1, sticky="ns")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.issue_tree.bind("<<TreeviewSelect>>", self._on_issue_selected)

        info = ttk.LabelFrame(right, text="비교 정보", padding=8)
        info.pack(fill=tk.X)
        self.issue_result_name_var = tk.StringVar(value="-")
        self.issue_source_name_var = tk.StringVar(value="-")
        self.issue_fp_var = tk.StringVar(value="-")
        ttk.Label(info, text="결과 파일명").grid(row=0, column=0, sticky="w")
        ttk.Label(info, textvariable=self.issue_result_name_var).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(info, text="원본 파일명").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(info, textvariable=self.issue_source_name_var).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        ttk.Label(info, text="지문").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(info, textvariable=self.issue_fp_var).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        info.columnconfigure(1, weight=1)

        cand_frame = ttk.LabelFrame(right, text="같은 지문 원본 후보", padding=8)
        cand_frame.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        self.issue_candidate_list = tk.Listbox(cand_frame, height=5)
        cand_scroll = ttk.Scrollbar(cand_frame, orient=tk.VERTICAL, command=self.issue_candidate_list.yview)
        self.issue_candidate_list.configure(yscrollcommand=cand_scroll.set)
        self.issue_candidate_list.grid(row=0, column=0, sticky="nsew")
        cand_scroll.grid(row=0, column=1, sticky="ns")
        cand_frame.columnconfigure(0, weight=1)
        cand_frame.rowconfigure(0, weight=1)
        self.issue_candidate_list.bind("<<ListboxSelect>>", self._on_issue_candidate_selected)

        preview = ttk.Frame(right)
        preview.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        preview.columnconfigure(0, weight=1)
        preview.columnconfigure(1, weight=1)
        preview.rowconfigure(1, weight=1)

        ttk.Label(preview, text="원본").grid(row=0, column=0, sticky="w")
        ttk.Label(preview, text="결과").grid(row=0, column=1, sticky="w")

        self.issue_source_image = ttk.Label(preview, text="미리보기 없음", anchor="center")
        self.issue_result_image = ttk.Label(preview, text="미리보기 없음", anchor="center")
        self.issue_source_image.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.issue_result_image.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        self.issue_source_path_var = tk.StringVar(value="")
        self.issue_result_path_var = tk.StringVar(value="")
        ttk.Label(preview, textvariable=self.issue_source_path_var).grid(
            row=2, column=0, sticky="ew", padx=(0, 6), pady=(6, 0)
        )
        ttk.Label(preview, textvariable=self.issue_result_path_var).grid(
            row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 0)
        )

    def _build_duplicate_tab(self) -> None:
        body = ttk.Panedwindow(self.dup_tab, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)

        group_cols = ("fingerprint", "count")
        self.dup_group_tree = ttk.Treeview(left, columns=group_cols, show="headings")
        self.dup_group_tree.heading("fingerprint", text="지문")
        self.dup_group_tree.heading("count", text="원본 개수")
        self.dup_group_tree.column("fingerprint", width=360, anchor="w")
        self.dup_group_tree.column("count", width=90, anchor="center")
        dup_group_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.dup_group_tree.yview)
        self.dup_group_tree.configure(yscrollcommand=dup_group_scroll.set)
        self.dup_group_tree.grid(row=0, column=0, sticky="nsew")
        dup_group_scroll.grid(row=0, column=1, sticky="ns")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.dup_group_tree.bind("<<TreeviewSelect>>", self._on_dup_group_selected)

        detail = ttk.LabelFrame(right, text="중복 원본 목록", padding=8)
        detail.pack(fill=tk.BOTH, expand=True)
        self.dup_candidate_list = tk.Listbox(detail)
        dup_cand_scroll = ttk.Scrollbar(detail, orient=tk.VERTICAL, command=self.dup_candidate_list.yview)
        self.dup_candidate_list.configure(yscrollcommand=dup_cand_scroll.set)
        self.dup_candidate_list.grid(row=0, column=0, sticky="nsew")
        dup_cand_scroll.grid(row=0, column=1, sticky="ns")
        detail.rowconfigure(0, weight=1)
        detail.columnconfigure(0, weight=1)
        self.dup_candidate_list.bind("<<ListboxSelect>>", self._on_dup_candidate_selected)

        self.dup_preview = ttk.Label(detail, text="미리보기 없음", anchor="center")
        self.dup_preview.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

    def _pick_source_dir(self) -> None:
        folder = filedialog.askdirectory(title="원본 폴더 선택")
        if folder:
            self.source_dir_var.set(folder)

    def _pick_result_dir(self) -> None:
        folder = filedialog.askdirectory(title="결과 폴더 선택")
        if folder:
            self.result_dir_var.set(folder)

    def _set_running(self, running: bool) -> None:
        self.run_button.configure(state="disabled" if running else "normal")
        self.cancel_button.configure(state="normal" if running else "disabled")
        self.mode_combo.configure(state="disabled" if running else "readonly")
        self.worker_spin.configure(state="disabled" if running else "normal")

    def _start_compare(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        source_dir = self.source_dir_var.get().strip()
        result_dir = self.result_dir_var.get().strip()
        if not source_dir or not Path(source_dir).is_dir():
            messagebox.showerror("오류", "원본 폴더를 먼저 선택하세요.")
            return
        if not result_dir or not Path(result_dir).is_dir():
            messagebox.showerror("오류", "결과 폴더를 먼저 선택하세요.")
            return

        self.records.clear()
        self.filtered_records.clear()
        self.issue_records.clear()
        self.source_entries_by_path.clear()
        self.source_duplicates.clear()
        self._image_cache.clear()
        self._image_cache_order.clear()

        self._clear_trees()
        self._set_summary("실행 중...")
        self.progress_var.set("준비 중...")

        self.stop_event.clear()
        self.worker = CompareWorker(
            source_dir=source_dir,
            result_dir=result_dir,
            mode=self.mode_var.get().strip(),
            workers=max(1, int(self.workers_var.get() or 1)),
            out_queue=self.queue,
            stop_event=self.stop_event,
        )
        self._set_running(True)
        self.worker.start()

    def _cancel_compare(self) -> None:
        self.stop_event.set()
        if self.worker is not None:
            self.worker.request_stop()
        self.progress_var.set("중지 요청됨...")

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True

        if self.worker is not None and self.worker.is_alive():
            self._cancel_compare()
            self.progress_var.set("종료 중... (작업 정리)")
            self.root.after(120, self._wait_worker_and_close)
            return

        self.root.destroy()

    def _wait_worker_and_close(self) -> None:
        worker = self.worker
        if worker is not None and worker.is_alive():
            self.root.after(120, self._wait_worker_and_close)
            return
        self.root.destroy()

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                msg_type = item.get("type")
                if msg_type == "stage":
                    self.progress_var.set(item.get("text", "작업 중..."))
                elif msg_type == "scan_done":
                    s_total = item.get("source_total", 0)
                    r_total = item.get("result_total", 0)
                    self.progress_var.set(f"스캔 완료 - 원본 {s_total}개 / 결과 {r_total}개")
                elif msg_type == "progress":
                    stage = item.get("stage", "")
                    done = item.get("done", 0)
                    total = item.get("total", 0)
                    self.progress_var.set(f"{stage}: {done}/{total}")
                elif msg_type == "cancelled":
                    self.progress_var.set("작업 취소됨")
                    self._set_running(False)
                elif msg_type == "error":
                    self._set_running(False)
                    messagebox.showerror("오류", item.get("message", "알 수 없는 오류"))
                    self.progress_var.set("오류")
                elif msg_type == "done":
                    self._set_running(False)
                    self._on_done(item)
        except queue.Empty:
            pass
        finally:
            try:
                self.root.after(80, self._poll_queue)
            except tk.TclError:
                pass

    def _on_done(self, item: dict[str, Any]) -> None:
        self.records = list(item.get("records", []))
        source_entries = list(item.get("source_entries", []))
        self.source_entries_by_path = {e.path: e for e in source_entries}
        self.source_duplicates = dict(item.get("source_duplicates", {}))
        counts = dict(item.get("counts", {}))
        elapsed = float(item.get("elapsed", 0.0))
        mode = str(item.get("mode", "hash"))

        self.issue_records = [r for r in self.records if r.status != STATUS_MATCH]
        self._refresh_result_view()
        self._refresh_issue_view()
        self._refresh_duplicate_view()

        summary = [
            f"지문 방식: {mode}",
            f"총 결과 파일 수: {len(self.records)}",
            f"{STATUS_MATCH}: {counts.get(STATUS_MATCH, 0)}",
            f"{STATUS_NAME_MISMATCH}: {counts.get(STATUS_NAME_MISMATCH, 0)}",
            f"{STATUS_FINGERPRINT_NOT_FOUND}: {counts.get(STATUS_FINGERPRINT_NOT_FOUND, 0)}",
            f"{STATUS_SOURCE_DUPLICATE}: {counts.get(STATUS_SOURCE_DUPLICATE, 0)}",
            f"{STATUS_READ_ERROR}: {counts.get(STATUS_READ_ERROR, 0)}",
            f"원본 중복 지문 그룹: {len(self.source_duplicates)}",
            f"소요 시간(초): {elapsed:.2f}",
        ]
        self._set_summary("\n".join(summary))
        self.progress_var.set("완료")

    def _clear_trees(self) -> None:
        for tree in (self.result_tree, self.issue_tree, self.dup_group_tree):
            for iid in tree.get_children():
                tree.delete(iid)
        self.issue_candidate_list.delete(0, tk.END)
        self.dup_candidate_list.delete(0, tk.END)
        self._clear_issue_preview()
        self._clear_dup_preview()

    def _set_summary(self, text: str) -> None:
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    def _refresh_result_view(self) -> None:
        selected_status = {s for s, var in self.result_filter_vars.items() if bool(var.get())}
        self.filtered_records = [r for r in self.records if r.status in selected_status]

        for iid in self.result_tree.get_children():
            self.result_tree.delete(iid)

        for idx, rec in enumerate(self.filtered_records):
            source_info = "-"
            if rec.source_candidates:
                if len(rec.source_candidates) == 1:
                    source_info = Path(rec.source_candidates[0]).name
                else:
                    source_info = f"{len(rec.source_candidates)}개 후보"
            self.result_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(rec.status, rec.result_name, source_info, rec.details),
            )

    def _on_result_tree_select(self, _event: Any) -> None:
        sel = self.result_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self.filtered_records):
            return
        rec = self.filtered_records[idx]
        if rec.status == STATUS_MATCH:
            return

        self.notebook.select(self.issue_tab)
        target_idx = -1
        for i, issue in enumerate(self.issue_records):
            if issue.result_path == rec.result_path:
                target_idx = i
                break
        if target_idx >= 0:
            self._select_issue_index(target_idx)

    def _refresh_issue_view(self) -> None:
        for iid in self.issue_tree.get_children():
            self.issue_tree.delete(iid)

        for idx, rec in enumerate(self.issue_records):
            self.issue_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(rec.status, rec.result_name, rec.details),
            )

        if self.issue_records:
            self._select_issue_index(0)
        else:
            self.issue_index_label.configure(text="0 / 0")
            self._clear_issue_preview()

    def _select_issue_index(self, idx: int) -> None:
        if not self.issue_records:
            return
        idx = max(0, min(idx, len(self.issue_records) - 1))
        iid = str(idx)
        self.issue_tree.selection_set(iid)
        self.issue_tree.focus(iid)
        self.issue_tree.see(iid)
        self._update_issue_detail(idx)

    def _on_issue_selected(self, _event: Any) -> None:
        sel = self.issue_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._update_issue_detail(idx)

    def _update_issue_detail(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.issue_records):
            self._clear_issue_preview()
            return

        rec = self.issue_records[idx]
        self.issue_index_label.configure(text=f"{idx + 1} / {len(self.issue_records)}")
        self.issue_result_name_var.set(rec.result_name)
        self.issue_fp_var.set(rec.result_fingerprint or "-")
        self.issue_result_path_var.set(rec.result_path)

        self.issue_candidate_list.delete(0, tk.END)
        for p in rec.source_candidates:
            self.issue_candidate_list.insert(tk.END, Path(p).name)

        result_photo = self._load_preview(rec.result_path, 620, 620)
        self._set_preview(self.issue_result_image, result_photo)

        if rec.source_candidates:
            self.issue_candidate_list.selection_set(0)
            self.issue_candidate_list.event_generate("<<ListboxSelect>>")
        else:
            self.issue_source_name_var.set("-")
            self.issue_source_path_var.set("-")
            self._set_preview(self.issue_source_image, None)

    def _on_issue_candidate_selected(self, _event: Any) -> None:
        sel_issue = self.issue_tree.selection()
        if not sel_issue:
            return
        issue_idx = int(sel_issue[0])
        if issue_idx < 0 or issue_idx >= len(self.issue_records):
            return
        rec = self.issue_records[issue_idx]

        cand_sel = self.issue_candidate_list.curselection()
        if not cand_sel:
            return
        cand_idx = cand_sel[0]
        if cand_idx < 0 or cand_idx >= len(rec.source_candidates):
            return
        src_path = rec.source_candidates[cand_idx]
        self.issue_source_name_var.set(Path(src_path).name)
        self.issue_source_path_var.set(src_path)
        source_photo = self._load_preview(src_path, 620, 620)
        self._set_preview(self.issue_source_image, source_photo)

    def _select_prev_issue(self) -> None:
        sel = self.issue_tree.selection()
        if not self.issue_records:
            return
        if not sel:
            self._select_issue_index(0)
            return
        idx = int(sel[0]) - 1
        self._select_issue_index(max(0, idx))

    def _select_next_issue(self) -> None:
        sel = self.issue_tree.selection()
        if not self.issue_records:
            return
        if not sel:
            self._select_issue_index(0)
            return
        idx = int(sel[0]) + 1
        self._select_issue_index(min(len(self.issue_records) - 1, idx))

    def _clear_issue_preview(self) -> None:
        self.issue_result_name_var.set("-")
        self.issue_source_name_var.set("-")
        self.issue_fp_var.set("-")
        self.issue_source_path_var.set("-")
        self.issue_result_path_var.set("-")
        self.issue_candidate_list.delete(0, tk.END)
        self._set_preview(self.issue_source_image, None)
        self._set_preview(self.issue_result_image, None)

    def _refresh_duplicate_view(self) -> None:
        for iid in self.dup_group_tree.get_children():
            self.dup_group_tree.delete(iid)

        for fp, entries in sorted(self.source_duplicates.items(), key=lambda x: (-len(x[1]), x[0])):
            self.dup_group_tree.insert("", tk.END, iid=fp, values=(fp, len(entries)))

        if self.dup_group_tree.get_children():
            first = self.dup_group_tree.get_children()[0]
            self.dup_group_tree.selection_set(first)
            self.dup_group_tree.focus(first)
            self.dup_group_tree.see(first)
            self._on_dup_group_selected(None)
        else:
            self._clear_dup_preview()

    def _on_dup_group_selected(self, _event: Any) -> None:
        sel = self.dup_group_tree.selection()
        self.dup_candidate_list.delete(0, tk.END)
        if not sel:
            self._clear_dup_preview()
            return
        fp = sel[0]
        entries = self.source_duplicates.get(fp, [])
        for e in entries:
            self.dup_candidate_list.insert(tk.END, Path(e.path).name)
        if entries:
            self.dup_candidate_list.selection_set(0)
            self.dup_candidate_list.event_generate("<<ListboxSelect>>")

    def _on_dup_candidate_selected(self, _event: Any) -> None:
        sel_group = self.dup_group_tree.selection()
        if not sel_group:
            return
        fp = sel_group[0]
        entries = self.source_duplicates.get(fp, [])
        cand_sel = self.dup_candidate_list.curselection()
        if not entries or not cand_sel:
            self._clear_dup_preview()
            return
        idx = cand_sel[0]
        if idx < 0 or idx >= len(entries):
            self._clear_dup_preview()
            return
        photo = self._load_preview(entries[idx].path, 720, 720)
        self._set_preview(self.dup_preview, photo)

    def _clear_dup_preview(self) -> None:
        self.dup_candidate_list.delete(0, tk.END)
        self._set_preview(self.dup_preview, None)

    def _load_preview(self, path: str, max_w: int, max_h: int) -> ImageTk.PhotoImage | None:
        key = (path, max_w, max_h)
        cached = self._image_cache.get(key)
        if cached is not None:
            return cached
        if not path or not Path(path).is_file():
            return None

        try:
            with Image.open(path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                else:
                    img = img.copy()
                img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
        except Exception:
            return None

        self._image_cache[key] = photo
        self._image_cache_order.append(key)
        while len(self._image_cache_order) > self._image_cache_limit:
            old = self._image_cache_order.pop(0)
            self._image_cache.pop(old, None)
        return photo

    @staticmethod
    def _set_preview(widget: ttk.Label, photo: ImageTk.PhotoImage | None) -> None:
        if photo is None:
            widget.configure(image="", text="미리보기 없음")
            widget.image = None
            return
        widget.configure(image=photo, text="")
        widget.image = photo


def main() -> None:
    root = tk.Tk()
    app = FingerprintCompareApp(root)
    root.minsize(1300, 760)
    root.mainloop()


if __name__ == "__main__":
    main()
