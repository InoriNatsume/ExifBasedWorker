from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .ops import normalize_tags_input, rename_variable, update_value


class InlineEditMixin:
    def _begin_variable_inline_edit(self, event: tk.Event) -> None:
        if not self.var_listbox:
            return
        index = self.var_listbox.nearest(int(event.y))
        if index < 0:
            return
        if index >= self.var_listbox.size():
            return
        self.var_listbox.selection_clear(0, tk.END)
        self.var_listbox.selection_set(index)
        self.var_listbox.activate(index)
        self._on_variable_select(event)
        self.var_listbox.after_idle(lambda i=index: self._start_inline_edit("variable", i))

    def _edit_selected_variable(self, _event: tk.Event) -> str:
        if not self.var_listbox:
            return "break"
        selected = self.var_listbox.curselection()
        if not selected:
            return "break"
        index = int(selected[0])
        self.var_listbox.after_idle(lambda i=index: self._start_inline_edit("variable", i))
        return "break"

    def _begin_value_inline_edit(self, event: tk.Event) -> None:
        if not self.value_listbox:
            return
        index = self.value_listbox.nearest(int(event.y))
        if index < 0:
            return
        if index >= self.value_listbox.size():
            return
        self.value_listbox.selection_clear(0, tk.END)
        self.value_listbox.selection_set(index)
        self.value_listbox.activate(index)
        self._on_value_select(event)
        self.value_listbox.after_idle(lambda i=index: self._start_inline_edit("value", i))

    def _edit_selected_value(self, _event: tk.Event) -> str:
        if not self.value_listbox:
            return "break"
        selected = self.value_listbox.curselection()
        if not selected:
            return "break"
        index = int(selected[0])
        self.value_listbox.after_idle(lambda i=index: self._start_inline_edit("value", i))
        return "break"

    def _begin_tag_inline_edit(self, event: tk.Event) -> None:
        if not self.tag_listbox:
            return
        index = self.tag_listbox.nearest(int(event.y))
        if index < 0:
            return
        if index >= self.tag_listbox.size():
            return
        self.tag_listbox.selection_clear(0, tk.END)
        self.tag_listbox.selection_set(index)
        self.tag_listbox.activate(index)
        self.tag_listbox.after_idle(lambda i=index: self._start_inline_edit("tag", i))

    def _edit_selected_tag(self, _event: tk.Event) -> str:
        if not self.tag_listbox:
            return "break"
        selected = self.tag_listbox.curselection()
        if not selected:
            return "break"
        index = int(selected[0])
        self.tag_listbox.after_idle(lambda i=index: self._start_inline_edit("tag", i))
        return "break"

    def _start_inline_edit(self, mode: str, index: int) -> None:
        self._end_inline_edit(commit=False)
        if mode == "variable":
            listbox = self.var_listbox
        elif mode == "value":
            listbox = self.value_listbox
        else:
            listbox = self.tag_listbox
        if not listbox:
            return
        bbox = listbox.bbox(index)
        if not bbox:
            return
        x, y, width, height = bbox
        if mode == "variable":
            preset = self.get_preset()
            if index >= len(preset.variables):
                return
            current_text = preset.variables[index].name
        else:
            current_text = listbox.get(index)

        entry = tk.Entry(listbox.master)
        entry.insert(0, current_text)
        entry.select_range(0, tk.END)
        entry.place(in_=listbox, x=x, y=y, width=width, height=height)
        entry.focus_set()

        self.inline_entry = entry
        self.inline_mode = mode
        self.inline_index = index
        self.inline_ignore_focus_out = True
        entry.after(120, self._enable_inline_focus_out)

        entry.bind("<Return>", lambda _e: self._end_inline_edit(commit=True))
        entry.bind("<Escape>", lambda _e: self._end_inline_edit(commit=False))
        entry.bind("<FocusOut>", lambda _e: self._on_inline_focus_out())

    def _enable_inline_focus_out(self) -> None:
        self.inline_ignore_focus_out = False

    def _on_inline_focus_out(self) -> None:
        if self.inline_ignore_focus_out:
            return
        self._end_inline_edit(commit=True)

    def _end_inline_edit(self, *, commit: bool) -> None:
        entry = self.inline_entry
        mode = self.inline_mode
        index = self.inline_index
        if not entry:
            return

        text = entry.get().strip()
        try:
            if commit and mode and index is not None:
                if mode == "variable":
                    self._commit_inline_variable_name(index, text)
                elif mode == "value":
                    self._commit_inline_value_name(index, text)
                elif mode == "tag":
                    self._commit_inline_tag(index, text)
        finally:
            if entry.winfo_exists():
                entry.destroy()
            self.inline_entry = None
            self.inline_mode = None
            self.inline_index = None
            self.inline_ignore_focus_out = False

    def _commit_inline_variable_name(self, var_idx: int, variable_name: str) -> None:
        if not variable_name:
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        if preset.variables[var_idx].name == variable_name:
            return
        try:
            new_preset = rename_variable(preset, var_idx, variable_name)
            self._apply_preset(new_preset, f"변수 이름 변경: {variable_name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _commit_inline_value_name(self, value_idx: int, value_name: str) -> None:
        if not value_name:
            return
        var_idx = self._selected_var_index()
        if var_idx is None:
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        values = preset.variables[var_idx].values
        if value_idx >= len(values):
            return
        value = values[value_idx]
        if value.name == value_name:
            return
        try:
            new_preset = update_value(preset, var_idx, value_idx, value_name, list(value.tags))
            self._apply_preset(new_preset, f"값 이름 변경: {value_name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))

    def _commit_inline_tag(self, tag_idx: int, new_tag_text: str) -> None:
        var_idx = self._selected_var_index()
        value_idx = self._selected_value_index()
        if var_idx is None or value_idx is None:
            return
        preset = self.get_preset()
        if var_idx >= len(preset.variables):
            return
        values = preset.variables[var_idx].values
        if value_idx >= len(values):
            return
        value = values[value_idx]
        if tag_idx >= len(value.tags):
            return
        parsed = normalize_tags_input(new_tag_text)
        if len(parsed) != 1:
            return
        new_tag = parsed[0]
        if value.tags[tag_idx] == new_tag:
            return
        updated_tags = list(value.tags)
        updated_tags[tag_idx] = new_tag
        try:
            new_preset = update_value(preset, var_idx, value_idx, value.name, updated_tags)
            self._apply_preset(new_preset, f"태그 변경: {value.name}")
        except Exception as exc:
            messagebox.showerror("템플릿", str(exc))
