from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Callable
from uuid import uuid4

from core.extract import extract_tags_from_image
from core.utils import remove_common_tags


def _iter_image_files(folder: str | Path) -> list[Path]:
    folder_path = Path(folder)
    results: list[Path] = []
    for root, _dirs, files in os.walk(folder_path):
        for name in files:
            lower = name.lower()
            if lower.endswith((".png", ".webp", ".jpg", ".jpeg")):
                results.append(Path(root) / name)
    results.sort()
    return results


def build_nais_from_folder(
    folder: str | Path,
    *,
    include_negative: bool = False,
    progress_step: int = 200,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[dict, dict]:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise ValueError(f"not a folder: {folder_path}")

    image_paths = _iter_image_files(folder_path)
    if not image_paths:
        raise ValueError("no images found")

    tags_by_path: list[tuple[Path, list[str]]] = []
    total = len(image_paths)
    for idx, path in enumerate(image_paths, start=1):
        tags = extract_tags_from_image(str(path), include_negative)
        tags_by_path.append((path, tags))
        if progress_cb and progress_step > 0:
            if idx % progress_step == 0 or idx == total:
                progress_cb(idx, total)

    unique_lists, common_tags = remove_common_tags([tags for _path, tags in tags_by_path])
    created_at = int(time.time() * 1000)
    scenes: list[dict] = []
    empty_unique = 0

    for idx, (path, _tags) in enumerate(tags_by_path):
        unique_tags = unique_lists[idx]
        if not unique_tags:
            empty_unique += 1
        scenes.append(
            {
                "id": uuid4().hex,
                "name": path.stem,
                "scenePrompt": ", ".join(unique_tags),
                "queueCount": 0,
                "images": [],
                "createdAt": created_at,
            }
        )

    payload = {
        "id": uuid4().hex,
        "name": folder_path.name,
        "scenes": scenes,
        "createdAt": created_at,
    }
    stats = {
        "total": total,
        "common_count": len(common_tags),
        "empty_unique": empty_unique,
        "common_tags": common_tags,
    }
    return payload, stats


def save_nais(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
