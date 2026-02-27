from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
import queue
import re
import shutil

from core.match import iter_search_results
from core.utils import ensure_unique_name, render_template, sanitize_filename
from .worker import init_worker, process_image


def _compute_chunksize(total: int) -> int:
    cpu_count = multiprocessing.cpu_count() or 2
    return max(10, total // (cpu_count * 20) if total else 10)


def rename_task(
    out_queue: "queue.Queue",
    image_paths: list[str],
    variable_specs: list[dict],
    order: list[str],
    template: str,
    prefix_mode: bool,
    dry_run: bool,
    include_negative: bool,
) -> None:
    reserved = {Path(path).name.lower() for path in image_paths}
    chunksize = _compute_chunksize(len(image_paths))

    with multiprocessing.Pool(
        processes=multiprocessing.cpu_count(),
        initializer=init_worker,
        initargs=(variable_specs, include_negative),
    ) as pool:
        for result in pool.imap_unordered(process_image, image_paths, chunksize=chunksize):
            path = result.get("path")
            if result.get("error"):
                out_queue.put(
                    (
                        "result",
                        "ERROR",
                        {"source": path, "target": None, "message": str(result["error"])},
                    )
                )
                continue

            matches = result.get("matches", {})
            status = "OK"
            values_map: dict[str, str] = {}
            for key in order:
                match = matches.get(key)
                if not match or match.get("status") != "OK":
                    status = (
                        "CONFLICT"
                        if match and match.get("status") == "CONFLICT"
                        else "UNKNOWN"
                    )
                    break
                values_map[key] = match.get("values", [""])[0]

            if status != "OK":
                out_queue.put(
                    (
                        "result",
                        status,
                        {"source": path, "target": None, "message": None},
                    )
                )
                continue

            base_name = render_template(template, values_map)
            base_name = sanitize_filename(base_name)
            if prefix_mode:
                stem = Path(path).stem
                if base_name:
                    joiner = "" if base_name.endswith("_") else "_"
                    base_name = f"{base_name}{joiner}{stem}"
                else:
                    base_name = stem

            ext = Path(path).suffix
            new_name = ensure_unique_name(Path(path).parent, base_name, ext, reserved)
            target = str(Path(path).with_name(new_name))
            if not dry_run and target != path:
                try:
                    os.rename(path, target)
                except Exception as exc:
                    out_queue.put(
                        (
                            "result",
                            "ERROR",
                            {"source": path, "target": None, "message": str(exc)},
                        )
                    )
                    continue
            out_queue.put(
                ("result", "OK", {"source": path, "target": target, "message": None})
            )

    out_queue.put(("done", None))


def move_task(
    out_queue: "queue.Queue",
    image_paths: list[str],
    variable_specs: list[dict],
    variable_name: str,
    template: str,
    target_root: str,
    dry_run: bool,
    include_negative: bool,
) -> None:
    chunksize = _compute_chunksize(len(image_paths))
    reserved_map: dict[str, set[str]] = {}

    with multiprocessing.Pool(
        processes=multiprocessing.cpu_count(),
        initializer=init_worker,
        initargs=(variable_specs, include_negative),
    ) as pool:
        for result in pool.imap_unordered(process_image, image_paths, chunksize=chunksize):
            path = result.get("path")
            if result.get("error"):
                out_queue.put(
                    (
                        "result",
                        "ERROR",
                        {"source": path, "target": None, "message": str(result["error"])},
                    )
                )
                continue

            matches = result.get("matches", {})
            match = matches.get(variable_name, {})
            status = match.get("status") or "UNKNOWN"

            if status != "OK":
                out_queue.put(
                    (
                        "result",
                        status,
                        {"source": path, "target": None, "message": None},
                    )
                )
                continue

            value_name = match.get("values", [""])[0]
            folder_name = render_template(template, {"value": value_name})
            folder_name = sanitize_filename(folder_name)
            if not folder_name:
                out_queue.put(
                    (
                        "result",
                        "ERROR",
                        {"source": path, "target": None, "message": "empty folder name"},
                    )
                )
                continue

            target_folder = str(Path(target_root) / folder_name)
            if target_folder not in reserved_map:
                try:
                    names = {
                        p.name.lower()
                        for p in Path(target_folder).glob("*")
                        if p.is_file()
                    }
                except FileNotFoundError:
                    names = set()
                reserved_map[target_folder] = names

            reserved = reserved_map[target_folder]
            ext = Path(path).suffix
            base = Path(path).stem
            new_name = ensure_unique_name(target_folder, base, ext, reserved)
            target = str(Path(target_folder) / new_name)

            if not dry_run:
                Path(target_folder).mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(path, target)
                except Exception as exc:
                    out_queue.put(
                        (
                            "result",
                            "ERROR",
                            {"source": path, "target": None, "message": str(exc)},
                        )
                    )
                    continue
            out_queue.put(
                ("result", "OK", {"source": path, "target": target, "message": None})
            )

    out_queue.put(("done", None))


_STRIP_RE = re.compile(r"^(?P<base>.+)@@@\\d+$")


def strip_suffix_task(
    out_queue: "queue.Queue",
    image_paths: list[str],
    dry_run: bool,
) -> None:
    reserved = {Path(path).name.lower() for path in image_paths}

    for path in image_paths:
        stem = Path(path).stem
        match = _STRIP_RE.match(stem)
        if not match:
            out_queue.put(
                ("result", "SKIP", {"source": path, "target": None, "message": None})
            )
            continue

        base = match.group("base")
        ext = Path(path).suffix
        candidate = f"{base}{ext}"
        candidate_lower = candidate.lower()
        if candidate_lower in reserved and candidate_lower != Path(path).name.lower():
            out_queue.put(
                (
                    "result",
                    "ERROR",
                    {"source": path, "target": None, "message": "target exists"},
                )
            )
            continue

        target = str(Path(path).with_name(candidate))
        if not dry_run and target != path:
            try:
                os.rename(path, target)
            except Exception as exc:
                out_queue.put(
                    (
                        "result",
                        "ERROR",
                        {"source": path, "target": None, "message": str(exc)},
                    )
                )
                continue

        reserved.add(candidate_lower)
        out_queue.put(
            ("result", "OK", {"source": path, "target": target, "message": None})
        )

    out_queue.put(("done", None))


def search_task(
    out_queue: "queue.Queue",
    image_paths: list[str],
    required_tags: list[str],
    include_negative: bool,
    progress_step: int = 200,
) -> None:
    total = len(image_paths)
    matches = 0
    errors = 0

    for idx, result in enumerate(
        iter_search_results(image_paths, required_tags, include_negative), start=1
    ):
        path = result.get("path")
        if result.get("error"):
            errors += 1
            out_queue.put(
                (
                    "result",
                    "ERROR",
                    {"source": path, "target": None, "message": result["error"]},
                )
            )
        elif result.get("matched"):
            matches += 1
            out_queue.put(
                ("result", "OK", {"source": path, "target": None, "message": None})
            )

        if idx % progress_step == 0 or idx == total:
            out_queue.put(("progress", idx, total, matches, errors))

    out_queue.put(("done", matches, errors))
