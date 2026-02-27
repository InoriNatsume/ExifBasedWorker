from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox


class WorkerMixin:
    def _run_async(self, task_name: str, work_fn, on_done, status_var: tk.StringVar) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning(task_name, "다른 작업이 실행 중입니다. 완료/취소 후 다시 시도하세요.")
            return

        self.sidebar_job_var.set(f"{task_name}: 시작")
        self.current_task_name = task_name
        self.worker_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_status_var = status_var
        self.worker_on_done = on_done

        def progress_cb(processed: int, total: int) -> None:
            if self.worker_queue:
                self.worker_queue.put(("progress", (processed, total)))

        def cancel_cb() -> bool:
            return bool(self.cancel_event and self.cancel_event.is_set())

        def runner() -> None:
            try:
                result = work_fn(progress_cb, cancel_cb)
                if self.worker_queue:
                    self.worker_queue.put(("done", result))
            except Exception as exc:
                if self.worker_queue:
                    self.worker_queue.put(("error", str(exc)))

        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()
        self.root.after(100, self._poll_worker_queue)

    def _poll_worker_queue(self) -> None:
        if not self.worker_queue:
            return
        finished = False
        try:
            while True:
                kind, payload = self.worker_queue.get_nowait()
                if kind == "progress":
                    processed, total = payload
                    if self.worker_status_var:
                        self.worker_status_var.set(f"진행 중... {processed}/{total}")
                    label = self.current_task_name or "작업"
                    self.sidebar_job_var.set(f"{label}: {processed}/{total}")
                elif kind == "done":
                    if self.worker_on_done:
                        self.worker_on_done(payload)
                    self.sidebar_job_var.set("작업 완료")
                    finished = True
                elif kind == "error":
                    messagebox.showerror("작업 오류", str(payload))
                    if self.worker_status_var:
                        self.worker_status_var.set(f"오류: {payload}")
                    self.sidebar_job_var.set("작업 오류")
                    logging.exception("작업 오류: %s", payload)
                    finished = True
        except queue.Empty:
            pass

        if finished:
            self.worker_queue = None
            self.worker_thread = None
            self.cancel_event = None
            self.worker_status_var = None
            self.worker_on_done = None
            self.current_task_name = None
            return

        self.root.after(100, self._poll_worker_queue)

    def _cancel_worker(self) -> None:
        if self.cancel_event and self.worker_thread and self.worker_thread.is_alive():
            self.cancel_event.set()
            logging.info("작업 취소 요청")
            if self.worker_status_var:
                self.worker_status_var.set("취소 요청됨...")
            self.sidebar_job_var.set("취소 요청됨...")

    @staticmethod
    def _status_counts(results: list[dict]) -> dict[str, int]:
        counts = {"OK": 0, "UNKNOWN": 0, "CONFLICT": 0, "ERROR": 0}
        for item in results:
            status = item.get("status")
            if status in counts:
                counts[status] += 1
        return counts
