from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import queue
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .result_panel_layout_mixin import ResultPanelLayoutMixin
from .result_panel_list_mixin import ResultPanelListMixin
from .result_panel_thumbnail_mixin import ResultPanelThumbnailMixin


class ResultPanel(ResultPanelListMixin, ResultPanelThumbnailMixin, ResultPanelLayoutMixin):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        list_ratio: float = 0.35,
        status_filters: tuple[str, ...] = ("OK", "UNKNOWN", "CONFLICT", "ERROR"),
    ) -> None:
        self.parent = parent
        self.records: list[dict] = []
        self.filtered_indices: list[int] = []
        self.preview_path: str | None = None
        self.selected_record_idx: int | None = None
        self.list_ratio = max(0.25, min(list_ratio, 0.75))
        self.status_filter_order = tuple(status_filters)
        self.pane: ttk.PanedWindow | None = None

        self.thumb_size = (128, 128)
        self.thumb_gap = 8
        self.chunk_size = 20
        self.visible_count = 0
        self.thumb_columns = 1
        self.thumb_labels_by_path: dict[str, list[tk.Label]] = {}
        self.thumb_card_frames: dict[int, tk.Frame] = {}
        self.rendered_thumb_indices: list[int] = []
        self.rendered_thumb_columns = 0
        self._last_thumb_source_indices: list[int] = []
        self.thumb_canvas: tk.Canvas | None = None
        self.thumb_scrollbar: ttk.Scrollbar | None = None
        self.thumb_inner: ttk.Frame | None = None
        self.thumb_window_id: int | None = None

        self.thumbnail_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="thumb")
        self.thumbnail_queue: queue.Queue[
            tuple[int, str, tuple[int, int], object | None, str | None]
        ] = queue.Queue()
        self.thumbnail_loading: set[str] = set()
        self.thumbnail_cache: OrderedDict[
            tuple[str, tuple[int, int]],
            ImageTk.PhotoImage,
        ] = OrderedDict()
        self.thumbnail_cache_limit = 360
        self.thumbnail_generation = 0
        self.thumbnail_process_batch = 10
        self._closed = False

        self.list_insert_batch = 120
        self.list_fill_cursor = 0
        self.list_fill_target_idx = 0
        self.list_fill_after_id: str | None = None

        self.show_thumbnails_var = tk.BooleanVar(value=True)
        self.auto_load_more_var = tk.BooleanVar(value=False)

        self.filter_vars = {
            "OK": tk.BooleanVar(value=True),
            "UNKNOWN": tk.BooleanVar(value=True),
            "CONFLICT": tk.BooleanVar(value=True),
            "ERROR": tk.BooleanVar(value=True),
            "SKIP": tk.BooleanVar(value=True),
        }

        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, padx=6, pady=4)
        for status in self.status_filter_order:
            ttk.Checkbutton(
                filter_frame,
                text=status,
                variable=self.filter_vars[status],
                command=self.apply_filters,
            ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            filter_frame,
            text="썸네일",
            variable=self.show_thumbnails_var,
            command=self._on_thumbnail_options_changed,
        ).pack(side=tk.LEFT, padx=(14, 4))
        ttk.Checkbutton(
            filter_frame,
            text="자동 더보기",
            variable=self.auto_load_more_var,
            command=self._on_thumbnail_options_changed,
        ).pack(side=tk.LEFT, padx=(10, 4))
        self.load_more_button = ttk.Button(
            filter_frame,
            text="더 보기",
            command=self._manual_load_more,
        )
        self.load_more_button.pack(side=tk.LEFT, padx=(0, 8))

        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.pane = pane
        pane.bind("<Configure>", self._on_pane_configure)

        left = ttk.Frame(pane)
        self.listbox = tk.Listbox(left, exportselection=False)
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        pane.add(left, weight=1)

        right = ttk.Frame(pane)
        self.preview_path_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.preview_path_var).pack(fill=tk.X, padx=4, pady=(2, 4))

        thumb_wrap = ttk.Frame(right)
        thumb_wrap.pack(fill=tk.BOTH, expand=True)
        self.thumb_canvas = tk.Canvas(thumb_wrap, highlightthickness=0, borderwidth=0)
        self.thumb_scrollbar = ttk.Scrollbar(
            thumb_wrap, orient=tk.VERTICAL, command=self._on_thumb_scrollbar
        )
        self.thumb_canvas.configure(yscrollcommand=self._on_thumb_yscroll)
        self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.thumb_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.thumb_inner = ttk.Frame(self.thumb_canvas)
        self.thumb_window_id = self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor="nw")
        self.thumb_inner.bind("<Configure>", self._on_thumb_inner_configure)
        self.thumb_canvas.bind("<Configure>", self._on_thumb_canvas_configure)
        self.thumb_canvas.bind("<MouseWheel>", self._on_thumb_mousewheel)
        self.thumb_inner.bind("<MouseWheel>", self._on_thumb_mousewheel)
        pane.add(right, weight=1)

        parent.bind("<Destroy>", self._on_parent_destroy, add="+")
        parent.after(120, self._set_initial_sash)
        parent.after(80, self._poll_thumbnail_queue)

    def clear(self) -> None:
        self._cancel_list_fill()
        self.records.clear()
        self.filtered_indices.clear()
        self.listbox.delete(0, tk.END)
        self.preview_path = None
        self.selected_record_idx = None
        self.preview_path_var.set("")
        self.visible_count = 0
        self._clear_thumbnail_grid()

    def set_results(self, records: list[dict]) -> None:
        self.records = list(records)
        self.apply_filters()

    def append_result(self, record: dict) -> None:
        self.records.append(record)
        self.apply_filters()

    def apply_filters(self) -> None:
        prev_path = self.preview_path
        self._cancel_list_fill()
        self.filtered_indices = []
        for idx, record in enumerate(self.records):
            if not self._is_visible(record.get("status")):
                continue
            self.filtered_indices.append(idx)

        if not self.filtered_indices:
            self.listbox.delete(0, tk.END)
            self.preview_path = None
            self.selected_record_idx = None
            self.preview_path_var.set("")
            self.visible_count = 0
            self._last_thumb_source_indices = []
            self._render_thumbnail_grid()
            return

        thumb_sources = self._thumbnail_source_indices()
        self._last_thumb_source_indices = thumb_sources
        total_thumbs = len(thumb_sources)
        chunk = self._chunk_size_for_current_layout()
        if self.visible_count <= 0:
            self.visible_count = min(chunk, total_thumbs)
        else:
            self.visible_count = min(self.visible_count, total_thumbs)

        target_list_idx = 0
        if prev_path:
            for list_idx, rec_idx in enumerate(self.filtered_indices):
                if self._record_preview_path(self.records[rec_idx]) == prev_path:
                    target_list_idx = list_idx
                    break

        self._start_list_fill(target_list_idx)
        self._render_thumbnail_grid()

    def _is_visible(self, status: str | None) -> bool:
        if not status:
            return True
        if status in self.filter_vars:
            return bool(self.filter_vars[status].get())
        return True

    def _to_text(self, record: dict) -> str:
        status = record.get("status") or "INFO"
        source = record.get("source") or ""
        target = record.get("target")
        message = record.get("message")
        if status == "OK" and target:
            return f"{status} | {source} -> {target}"
        if message:
            return f"{status} | {source} | {message}"
        return f"{status} | {source}"

    def _record_preview_path(self, record: dict) -> str:
        return str(record.get("preview") or record.get("target") or record.get("source") or "")
