from __future__ import annotations

import logging
from pathlib import Path
import queue
import tkinter as tk


class QueueLogHandler(logging.Handler):
    def __init__(self, output_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.output_queue = output_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.output_queue.put(msg)
        except Exception:
            self.handleError(record)


class AppLoggingMixin:
    def _setup_logging(self) -> None:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "app.log"

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # 중복 핸들러 방지
        if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        if not any(isinstance(h, QueueLogHandler) for h in root_logger.handlers):
            queue_handler = QueueLogHandler(self.log_queue)
            queue_handler.setFormatter(formatter)
            root_logger.addHandler(queue_handler)

        logging.getLogger(__name__).info("로그 파일: %s", log_path)

    def _poll_log_queue(self) -> None:
        if self.log_text:
            try:
                while True:
                    msg = self.log_queue.get_nowait()
                    self.log_text.insert(tk.END, msg + "\n")
                    self.log_text.see(tk.END)
            except queue.Empty:
                pass
        self.root.after(200, self._poll_log_queue)
