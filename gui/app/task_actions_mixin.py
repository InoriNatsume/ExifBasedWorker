from __future__ import annotations

import logging
from tkinter import filedialog, messagebox

from ..services import move_images, rename_images, search_images


class TaskActionsMixin:
    def _open_task_log(self, task: str) -> None:
        self._show_tab("log")
        if not self.log_notebook:
            return
        if task == "rename" and self.rename_log_tab_frame:
            self.log_notebook.select(self.rename_log_tab_frame)
        elif task == "move" and self.move_log_tab_frame:
            self.log_notebook.select(self.move_log_tab_frame)

    def _pick_search_folder(self) -> None:
        path = filedialog.askdirectory(title="검색 폴더 선택")
        if path:
            self.search_folder_var.set(path)

    def _run_search(self) -> None:
        folder = self.search_folder_var.get().strip()
        tags = self.search_tags_var.get().strip()
        include_negative = bool(self.search_include_negative_var.get())
        if not folder:
            messagebox.showwarning("검색", "폴더를 선택하세요.")
            return
        if not tags:
            messagebox.showwarning("검색", "검색 태그를 입력하세요.")
            return
        if self.search_result_panel:
            self.search_result_panel.clear()
        self.search_status_var.set("검색 중...")

        def work(progress_cb, cancel_cb):
            return search_images(
                folder,
                tags,
                include_negative=include_negative,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )

        def done(results):
            if self.search_result_panel:
                self.search_result_panel.set_results(results)
            ok_count = sum(1 for item in results if item.get("status") == "OK")
            err_count = sum(1 for item in results if item.get("status") == "ERROR")
            self.search_status_var.set(f"완료: 매치 {ok_count} / 오류 {err_count}")
            logging.info("검색 완료: match=%d error=%d", ok_count, err_count)

        self._run_async("검색", work, done, self.search_status_var)

    def _pick_rename_folder(self) -> None:
        path = filedialog.askdirectory(title="파일명 변경 폴더 선택")
        if path:
            self.rename_folder_var.set(path)

    def _run_rename(self) -> None:
        folder = self.rename_folder_var.get().strip()
        order_text = self.rename_order_var.get().strip()
        selected_template_text = self.rename_template_file_var.get().strip()
        dry_run = bool(self.rename_dry_run_var.get())
        prefix_mode = bool(self.rename_prefix_var.get())
        include_negative = bool(self.rename_include_negative_var.get())

        if not folder:
            messagebox.showwarning("파일명 변경", "폴더를 선택하세요.")
            return
        if not order_text:
            messagebox.showwarning("파일명 변경", "변수 순서를 입력하세요.")
            return
        try:
            task_preset, task_template_label = self._resolve_task_preset(selected_template_text)
        except Exception as exc:
            messagebox.showerror("파일명 변경", f"사용 템플릿 로드/검증 실패: {exc}")
            return

        if self.rename_result_panel:
            self.rename_result_panel.clear()
        self.rename_status_var.set("파일명 변경 실행 중...")

        def work(progress_cb, cancel_cb):
            return rename_images(
                task_preset,
                folder,
                order_text,
                dry_run=dry_run,
                prefix_mode=prefix_mode,
                include_negative=include_negative,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )

        def done(results):
            if self.rename_result_panel:
                self.rename_result_panel.set_results(results)
            counts = self._status_counts(results)
            self.rename_status_var.set(
                f"완료: OK {counts['OK']} UNKNOWN {counts['UNKNOWN']} "
                f"CONFLICT {counts['CONFLICT']} ERROR {counts['ERROR']}"
            )
            self._write_task_result_log(
                "rename",
                results,
                header=(
                    f"폴더={folder} | 사용템플릿={task_template_label} | "
                    f"순서={order_text} | 드라이런={dry_run}"
                ),
            )
            logging.info("파일명 변경 완료: %s", counts)

        self._run_async("파일명 변경", work, done, self.rename_status_var)

    def _pick_move_source(self) -> None:
        path = filedialog.askdirectory(title="작업 폴더 선택")
        if path:
            self.move_source_var.set(path)

    def _run_move(self) -> None:
        source = self.move_source_var.get().strip()
        target = source
        selected_template_text = self.move_template_file_var.get().strip()
        order_items = [item.strip() for item in self.move_order_var.get().split(",") if item.strip()]
        folder_template = "/".join(f"[{name}]" for name in order_items)
        dry_run = bool(self.move_dry_run_var.get())
        include_negative = bool(self.move_include_negative_var.get())

        if not source:
            messagebox.showwarning("분류", "작업 폴더를 선택하세요.")
            return
        if not order_items:
            messagebox.showwarning("분류", "분류 변수 순서를 입력하세요.")
            return
        try:
            task_preset, task_template_label = self._resolve_task_preset(selected_template_text)
        except Exception as exc:
            messagebox.showerror("분류", f"사용 템플릿 로드/검증 실패: {exc}")
            return
        if self.move_result_panel:
            self.move_result_panel.clear()
        self.move_status_var.set("분류 실행 중...")

        def work(progress_cb, cancel_cb):
            return move_images(
                task_preset,
                source,
                target,
                order_items,
                folder_template=folder_template,
                dry_run=dry_run,
                include_negative=include_negative,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )

        def done(results):
            if self.move_result_panel:
                self.move_result_panel.set_results(results)
            counts = self._status_counts(results)
            self.move_status_var.set(
                f"완료: OK {counts['OK']} UNKNOWN {counts['UNKNOWN']} "
                f"CONFLICT {counts['CONFLICT']} ERROR {counts['ERROR']}"
            )
            self._write_task_result_log(
                "move",
                results,
                header=(
                    f"작업폴더={source} | 사용템플릿={task_template_label} | "
                    f"순서={','.join(order_items)} | "
                    f"드라이런={dry_run}"
                ),
            )
            logging.info("분류 완료: %s", counts)

        self._run_async("분류", work, done, self.move_status_var)
