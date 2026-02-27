from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from ..result_panel import ResultPanel
from ..state import AppState
from ..template_editor import TemplateEditorPanel
from .logging_mixin import AppLoggingMixin, QueueLogHandler
from .task_actions_mixin import TaskActionsMixin
from .task_log_mixin import TaskLogMixin
from .task_template_mixin import TaskTemplateSelectionMixin
from .template_mixin import TemplateWorkflowMixin
from .ui_mixin import AppUiMixin
from .view_vars import create_view_vars
from .worker_mixin import WorkerMixin


class ExifTkApp(
    AppLoggingMixin,
    AppUiMixin,
    TemplateWorkflowMixin,
    TaskTemplateSelectionMixin,
    TaskActionsMixin,
    TaskLogMixin,
    WorkerMixin,
):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EXIF Template Tool (Tkinter)")
        self.root.geometry("1680x980")
        self.root.minsize(1320, 820)

        self.state = AppState.create()
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._init_worker_state()
        self._init_view_state()
        self._init_widget_state()

        self._setup_logging()
        self._build_ui()
        self._refresh_template_ui()
        self.root.after(100, self._poll_log_queue)

    def _init_worker_state(self) -> None:
        self.worker_thread: threading.Thread | None = None
        self.worker_queue: queue.Queue | None = None
        self.cancel_event: threading.Event | None = None
        self.worker_status_var: tk.StringVar | None = None
        self.worker_on_done = None
        self.current_task_name: str | None = None

    def _init_view_state(self) -> None:
        self.view_vars = create_view_vars()
        # 기존 믹스인 코드 호환을 위해 이름을 유지한다.
        self.template_path_var = self.view_vars.template.path
        self.template_status_var = self.view_vars.template.status
        self.build_folder_var = self.view_vars.template.build_folder
        self.build_preset_json_var = self.view_vars.template.build_preset_json
        self.build_variable_var = self.view_vars.template.build_variable
        self.build_include_negative_var = self.view_vars.template.build_include_negative

        self.search_folder_var = self.view_vars.search.folder
        self.search_tags_var = self.view_vars.search.tags
        self.search_include_negative_var = self.view_vars.search.include_negative
        self.search_status_var = self.view_vars.search.status

        self.rename_folder_var = self.view_vars.rename.folder
        self.rename_order_var = self.view_vars.rename.order
        self.rename_template_file_var = self.view_vars.rename.template_file
        self.rename_dry_run_var = self.view_vars.rename.dry_run
        self.rename_prefix_var = self.view_vars.rename.prefix_mode
        self.rename_include_negative_var = self.view_vars.rename.include_negative
        self.rename_status_var = self.view_vars.rename.status

        self.move_source_var = self.view_vars.move.source
        self.move_template_file_var = self.view_vars.move.template_file
        self.move_order_var = self.view_vars.move.order
        self.move_dry_run_var = self.view_vars.move.dry_run
        self.move_include_negative_var = self.view_vars.move.include_negative
        self.move_status_var = self.view_vars.move.status

        self.rename_log_summary_var = self.view_vars.logs.rename_summary
        self.move_log_summary_var = self.view_vars.logs.move_summary
        self.rename_log_filter_vars = self.view_vars.logs.rename_filters
        self.move_log_filter_vars = self.view_vars.logs.move_filters
        self.sidebar_job_var = self.view_vars.sidebar.job

    def _init_widget_state(self) -> None:
        self.template_editor: TemplateEditorPanel | None = None

        self.search_result_panel: ResultPanel | None = None
        self.rename_result_panel: ResultPanel | None = None
        self.move_result_panel: ResultPanel | None = None
        self.log_text: tk.Text | None = None
        self.rename_log_tree: ttk.Treeview | None = None
        self.move_log_tree: ttk.Treeview | None = None
        self.rename_template_combo: ttk.Combobox | None = None
        self.move_template_combo: ttk.Combobox | None = None
        self.task_template_paths: dict[str, str] = {}
        self.log_notebook: ttk.Notebook | None = None
        self.rename_log_tab_frame: ttk.Frame | None = None
        self.move_log_tab_frame: ttk.Frame | None = None
        self.rename_log_header = ""
        self.move_log_header = ""
        self.rename_log_records: list[dict] = []
        self.move_log_records: list[dict] = []
        self.nav_buttons: dict[str, ttk.Button] = {}
        self.tab_frames: dict[str, ttk.Frame] = {}
        self.active_tab = "template"


def main() -> None:
    root = tk.Tk()
    ExifTkApp(root)
    root.mainloop()


__all__ = ["ExifTkApp", "QueueLogHandler", "main"]
