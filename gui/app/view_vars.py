from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass
class TemplateVars:
    path: tk.StringVar
    status: tk.StringVar
    build_folder: tk.StringVar
    build_preset_json: tk.StringVar
    build_variable: tk.StringVar
    build_include_negative: tk.BooleanVar


@dataclass
class SearchVars:
    folder: tk.StringVar
    tags: tk.StringVar
    include_negative: tk.BooleanVar
    status: tk.StringVar


@dataclass
class RenameVars:
    folder: tk.StringVar
    order: tk.StringVar
    template_file: tk.StringVar
    dry_run: tk.BooleanVar
    prefix_mode: tk.BooleanVar
    include_negative: tk.BooleanVar
    status: tk.StringVar


@dataclass
class MoveVars:
    source: tk.StringVar
    template_file: tk.StringVar
    order: tk.StringVar
    dry_run: tk.BooleanVar
    include_negative: tk.BooleanVar
    status: tk.StringVar


@dataclass
class LogVars:
    rename_summary: tk.StringVar
    move_summary: tk.StringVar
    rename_filters: dict[str, tk.BooleanVar]
    move_filters: dict[str, tk.BooleanVar]


@dataclass
class SidebarVars:
    job: tk.StringVar


@dataclass
class AppViewVars:
    template: TemplateVars
    search: SearchVars
    rename: RenameVars
    move: MoveVars
    logs: LogVars
    sidebar: SidebarVars


def create_view_vars() -> AppViewVars:
    return AppViewVars(
        template=TemplateVars(
            path=tk.StringVar(value=""),
            status=tk.StringVar(value="대기"),
            build_folder=tk.StringVar(value=""),
            build_preset_json=tk.StringVar(value=""),
            build_variable=tk.StringVar(value=""),
            build_include_negative=tk.BooleanVar(value=False),
        ),
        search=SearchVars(
            folder=tk.StringVar(value=""),
            tags=tk.StringVar(value=""),
            include_negative=tk.BooleanVar(value=False),
            status=tk.StringVar(value="대기"),
        ),
        rename=RenameVars(
            folder=tk.StringVar(value=""),
            order=tk.StringVar(value=""),
            template_file=tk.StringVar(value=""),
            dry_run=tk.BooleanVar(value=True),
            prefix_mode=tk.BooleanVar(value=False),
            include_negative=tk.BooleanVar(value=False),
            status=tk.StringVar(value="대기"),
        ),
        move=MoveVars(
            source=tk.StringVar(value=""),
            template_file=tk.StringVar(value=""),
            order=tk.StringVar(value=""),
            dry_run=tk.BooleanVar(value=True),
            include_negative=tk.BooleanVar(value=False),
            status=tk.StringVar(value="대기"),
        ),
        logs=LogVars(
            rename_summary=tk.StringVar(value="대기"),
            move_summary=tk.StringVar(value="대기"),
            rename_filters={
                "OK": tk.BooleanVar(value=True),
                "UNKNOWN": tk.BooleanVar(value=True),
                "CONFLICT": tk.BooleanVar(value=True),
                "ERROR": tk.BooleanVar(value=True),
            },
            move_filters={
                "OK": tk.BooleanVar(value=True),
                "UNKNOWN": tk.BooleanVar(value=True),
                "CONFLICT": tk.BooleanVar(value=True),
                "ERROR": tk.BooleanVar(value=True),
            },
        ),
        sidebar=SidebarVars(
            job=tk.StringVar(value="작업 대기"),
        ),
    )
