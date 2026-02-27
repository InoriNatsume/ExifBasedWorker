from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
import queue
import tkinter as tk

from PIL import Image, ImageTk
from tkinter import ttk


class ResultPanelThumbnailMixin:
    def _thumbnail_source_indices(self) -> list[int]:
        if not bool(self.show_thumbnails_var.get()):
            return []
        if not bool(self.thumb_ok_only_var.get()):
            return list(self.filtered_indices)
        return [
            rec_idx
            for rec_idx in self.filtered_indices
            if str(self.records[rec_idx].get("status") or "") == "OK"
        ]

    def _chunk_size_for_current_layout(self) -> int:
        # 화면 폭(열 수)에 따라 한 번에 불러올 썸네일 개수를 제한해 프리징을 줄인다.
        if not bool(self.auto_load_more_var.get()):
            return max(8, self.chunk_size)
        dynamic = max(1, self.thumb_columns) * 4
        return max(self.chunk_size, dynamic)

    def _on_thumbnail_options_changed(self) -> None:
        self.visible_count = 0
        self.apply_filters()

    def _clear_thumbnail_grid(self) -> None:
        if not self.thumb_inner:
            return
        self.thumbnail_generation += 1
        for child in self.thumb_inner.winfo_children():
            child.destroy()
        self.thumbnail_loading.clear()
        self.thumb_labels_by_path.clear()
        self.thumb_card_frames.clear()
        self.rendered_thumb_indices.clear()
        self.rendered_thumb_columns = 0
        try:
            while True:
                self.thumbnail_queue.get_nowait()
        except queue.Empty:
            pass
        if self.thumb_canvas:
            self.thumb_canvas.configure(scrollregion=(0, 0, 0, 0))

    def _render_thumbnail_grid(self) -> None:
        if not self.thumb_inner:
            return
        if not bool(self.show_thumbnails_var.get()):
            self._clear_thumbnail_grid()
            ttk.Label(self.thumb_inner, text="썸네일 표시 꺼짐").pack(padx=10, pady=10)
            self._update_load_more_button()
            return

        source_indices = list(self._last_thumb_source_indices or self._thumbnail_source_indices())
        shown_indices = self._shown_thumbnail_indices(source_indices)
        if not shown_indices:
            self._clear_thumbnail_grid()
            if bool(self.thumb_ok_only_var.get()) and self.filtered_indices:
                text = "표시할 OK 썸네일 없음"
            else:
                text = "결과 없음"
            ttk.Label(self.thumb_inner, text=text).pack(padx=10, pady=10)
            self._update_load_more_button()
            return

        columns = max(1, self.thumb_columns)
        incremental = (
            self.rendered_thumb_columns == columns
            and len(self.rendered_thumb_indices) <= len(shown_indices)
            and shown_indices[: len(self.rendered_thumb_indices)] == self.rendered_thumb_indices
        )
        if not incremental:
            self._clear_thumbnail_grid()
            self.rendered_thumb_columns = columns
        start = len(self.rendered_thumb_indices)

        for col in range(columns):
            self.thumb_inner.columnconfigure(col, weight=1)

        for pos, rec_idx in enumerate(shown_indices[start:], start=start):
            row = pos // columns
            col = pos % columns
            record = self.records[rec_idx]
            image_path = self._record_preview_path(record)
            caption = Path(image_path).name if image_path else "-"

            card = tk.Frame(self.thumb_inner, bd=1, relief=tk.GROOVE)
            card.grid(row=row, column=col, sticky="nsew", padx=self.thumb_gap // 2, pady=self.thumb_gap // 2)
            card.configure(width=self.thumb_size[0] + 12, height=self.thumb_size[1] + 34)
            card.grid_propagate(False)
            self.thumb_card_frames[rec_idx] = card

            img_label = tk.Label(card, text="로딩...", anchor="center")
            img_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 2))

            name_label = tk.Label(
                card,
                text=caption,
                anchor="w",
                justify=tk.LEFT,
                wraplength=self.thumb_size[0],
            )
            name_label.pack(fill=tk.X, padx=4, pady=(0, 4))

            self.thumb_labels_by_path.setdefault(image_path, []).append(img_label)
            self._request_thumbnail(image_path)
            self.rendered_thumb_indices.append(rec_idx)

            for widget in (card, img_label, name_label):
                widget.bind("<Button-1>", lambda _e, idx=rec_idx: self._on_thumbnail_click(idx))

        self._update_selected_card_style()
        self._update_load_more_button()
        self._check_load_more()

    def _shown_thumbnail_indices(self, source_indices: list[int]) -> list[int]:
        total = len(source_indices)
        if total <= 0:
            return []
        count = min(max(1, self.visible_count), total)
        selected = self.selected_record_idx
        if selected is None:
            return source_indices[:count]
        try:
            center = source_indices.index(selected)
        except ValueError:
            return source_indices[:count]

        half = count // 2
        start = max(0, center - half)
        end = start + count
        if end > total:
            end = total
            start = max(0, end - count)
        return source_indices[start:end]

    def _update_selected_card_style(self) -> None:
        for rec_idx, card in self.thumb_card_frames.items():
            if not card.winfo_exists():
                continue
            if rec_idx == self.selected_record_idx:
                card.configure(relief=tk.SOLID, bd=2, highlightthickness=1)
            else:
                card.configure(relief=tk.GROOVE, bd=1, highlightthickness=0)

    def _request_thumbnail(self, path: str) -> None:
        if not path:
            self._apply_thumbnail_error(path, "미리보기 없음")
            return

        if not bool(self.show_thumbnails_var.get()):
            self._apply_thumbnail_error(path, "썸네일 비활성")
            return

        size = self.thumb_size
        cached = self._cache_get(path, size)
        if cached is not None:
            self._apply_thumbnail_image(path, cached)
            return

        if path in self.thumbnail_loading:
            return
        self.thumbnail_loading.add(path)
        generation = self.thumbnail_generation
        future = self.thumbnail_executor.submit(self._load_thumbnail_image, path, size)
        future.add_done_callback(
            lambda f, p=path, s=size, g=generation: self._on_thumbnail_loaded(g, p, s, f)
        )

    def _on_thumbnail_loaded(
        self,
        generation: int,
        path: str,
        size: tuple[int, int],
        future: Future,
    ) -> None:
        try:
            image = future.result()
            self.thumbnail_queue.put((generation, path, size, image, None))
        except Exception as exc:
            self.thumbnail_queue.put((generation, path, size, None, str(exc)))

    @staticmethod
    def _load_thumbnail_image(path: str, size: tuple[int, int]) -> Image.Image | None:
        image_path = Path(path)
        if not image_path.exists():
            return None
        with Image.open(image_path) as opened:
            img = opened.convert("RGB")
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        img.thumbnail(size, resample)
        return img

    def _poll_thumbnail_queue(self) -> None:
        if self._closed or not self.parent.winfo_exists():
            return
        try:
            processed = 0
            while processed < self.thumbnail_process_batch:
                generation, path, size, image, err = self.thumbnail_queue.get_nowait()
                processed += 1
                if generation != self.thumbnail_generation:
                    self.thumbnail_loading.discard(path)
                    continue
                self.thumbnail_loading.discard(path)
                if image is None:
                    self._apply_thumbnail_error(path, "미리보기 실패" if err else "미리보기 없음")
                    continue
                photo = ImageTk.PhotoImage(image)
                self._cache_put(path, size, photo)
                self._apply_thumbnail_image(path, photo)
        except queue.Empty:
            pass
        self.parent.after(80, self._poll_thumbnail_queue)

    def _apply_thumbnail_image(self, path: str, photo: ImageTk.PhotoImage) -> None:
        labels = self.thumb_labels_by_path.get(path, [])
        for label in labels:
            if not label.winfo_exists():
                continue
            label.configure(image=photo, text="")
            label.image = photo

    def _apply_thumbnail_error(self, path: str, text: str) -> None:
        labels = self.thumb_labels_by_path.get(path, [])
        for label in labels:
            if not label.winfo_exists():
                continue
            label.configure(text=text, image="")
            label.image = None

    def _cache_get(self, path: str, size: tuple[int, int]) -> ImageTk.PhotoImage | None:
        key = (path, size)
        photo = self.thumbnail_cache.get(key)
        if photo is not None:
            self.thumbnail_cache.move_to_end(key)
        return photo

    def _cache_put(self, path: str, size: tuple[int, int], photo: ImageTk.PhotoImage) -> None:
        key = (path, size)
        self.thumbnail_cache[key] = photo
        self.thumbnail_cache.move_to_end(key)
        while len(self.thumbnail_cache) > self.thumbnail_cache_limit:
            self.thumbnail_cache.popitem(last=False)

    def _on_thumb_scrollbar(self, *args: str) -> None:
        if not self.thumb_canvas:
            return
        self.thumb_canvas.yview(*args)
        self._check_load_more()

    def _on_thumb_yscroll(self, first: str, last: str) -> None:
        if self.thumb_scrollbar:
            self.thumb_scrollbar.set(first, last)
        try:
            self._check_load_more(last=float(last))
        except Exception:
            pass

    def _on_thumb_mousewheel(self, event: tk.Event) -> str:
        if not self.thumb_canvas:
            return "break"
        delta = int(-event.delta / 120) if getattr(event, "delta", 0) else 0
        if delta != 0:
            self.thumb_canvas.yview_scroll(delta, "units")
            self._check_load_more()
        return "break"

    def _on_thumb_inner_configure(self, _event: tk.Event) -> None:
        if not self.thumb_canvas:
            return
        bbox = self.thumb_canvas.bbox("all")
        if bbox:
            self.thumb_canvas.configure(scrollregion=bbox)

    def _on_thumb_canvas_configure(self, event: tk.Event) -> None:
        if not self.thumb_canvas:
            return
        if self.thumb_window_id is not None:
            self.thumb_canvas.itemconfigure(self.thumb_window_id, width=max(1, int(event.width)))
        new_cols = max(1, max(1, int(event.width)) // (self.thumb_size[0] + self.thumb_gap * 2))
        if new_cols != self.thumb_columns:
            self.thumb_columns = new_cols
            self._render_thumbnail_grid()

    def _check_load_more(self, *, last: float | None = None) -> None:
        if not self.thumb_canvas:
            return
        if not bool(self.show_thumbnails_var.get()):
            return
        if not bool(self.auto_load_more_var.get()):
            self._update_load_more_button()
            return
        total = len(self._last_thumb_source_indices or self._thumbnail_source_indices())
        if self.visible_count >= total:
            self._update_load_more_button()
            return
        if last is None:
            try:
                _, last = self.thumb_canvas.yview()
            except Exception:
                return
        if last < 0.92:
            return
        prev = self.visible_count
        self.visible_count = min(total, self.visible_count + self._chunk_size_for_current_layout())
        if self.visible_count != prev:
            self._render_thumbnail_grid()
        else:
            self._update_load_more_button()

    def _manual_load_more(self) -> None:
        if not bool(self.show_thumbnails_var.get()):
            return
        total = len(self._last_thumb_source_indices or self._thumbnail_source_indices())
        if self.visible_count >= total:
            self._update_load_more_button()
            return
        self.visible_count = min(total, self.visible_count + self._chunk_size_for_current_layout())
        self._render_thumbnail_grid()

    def _update_load_more_button(self) -> None:
        if not hasattr(self, "load_more_button"):
            return
        total = len(self._last_thumb_source_indices or self._thumbnail_source_indices())
        remain = max(0, total - self.visible_count)
        if not bool(self.show_thumbnails_var.get()) or total <= 0:
            self.load_more_button.configure(text="더 보기", state=tk.DISABLED)
            return
        if bool(self.auto_load_more_var.get()):
            self.load_more_button.configure(text="자동", state=tk.DISABLED)
            return
        if remain <= 0:
            self.load_more_button.configure(text="끝", state=tk.DISABLED)
            return
        step = min(remain, self._chunk_size_for_current_layout())
        self.load_more_button.configure(text=f"더 보기 (+{step})", state=tk.NORMAL)
