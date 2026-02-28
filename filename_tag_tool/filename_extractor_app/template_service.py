from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .file_utils import iter_image_files, remove_common_tags
from .models import Preset, Variable, VariableValue
from .tag_extractor import extract_tags_from_image


def _tag_set(tags: list[str]) -> frozenset[str]:
    return frozenset(tag for tag in tags if tag)


def _filter_value_conflicts(values: list[VariableValue]) -> tuple[list[VariableValue], dict[str, Any]]:
    tag_sets: dict[frozenset[str], int] = {}
    entries: list[tuple[int, frozenset[str]]] = []
    duplicate_indices: set[int] = set()
    duplicate_pairs: list[tuple[int, int]] = []

    for idx, value in enumerate(values):
        tset = _tag_set(value.tags)
        if not tset:
            continue
        if tset in tag_sets:
            other_idx = tag_sets[tset]
            duplicate_pairs.append((idx, other_idx))
            duplicate_indices.add(idx)
            continue
        tag_sets[tset] = idx
        entries.append((idx, tset))

    subset_indices: set[int] = set()
    subset_pairs: list[tuple[int, int]] = []
    entries.sort(key=lambda item: len(item[1]))
    for pos, (idx, set_a) in enumerate(entries):
        for other_idx, set_b in entries[pos + 1 :]:
            if set_a.issubset(set_b):
                subset_pairs.append((idx, other_idx))
                subset_indices.add(idx)
                break

    removed_indices = duplicate_indices | subset_indices
    filtered = [value for idx, value in enumerate(values) if idx not in removed_indices]
    summary = {
        "duplicate_pairs": duplicate_pairs,
        "subset_pairs": subset_pairs,
        "removed_indices": sorted(removed_indices),
    }
    return filtered, summary


def build_variable_from_folder(
    folder: str,
    *,
    variable_name: str | None = None,
    include_negative: bool = False,
) -> tuple[Variable, dict[str, Any]]:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise ValueError(f"유효한 폴더가 아닙니다: {folder}")

    image_paths = iter_image_files(folder_path)
    if not image_paths:
        raise ValueError("이미지 파일이 없습니다. (.png/.webp/.jpg/.jpeg)")

    tags_by_path: list[tuple[str, list[str]]] = []
    for image_path in image_paths:
        tags = extract_tags_from_image(image_path, include_negative)
        tags_by_path.append((image_path, tags))

    unique_lists, common_tags = remove_common_tags([tags for _path, tags in tags_by_path])

    values: list[VariableValue] = []
    empty_unique = 0
    for idx, (image_path, _tags) in enumerate(tags_by_path):
        unique_tags = unique_lists[idx]
        if not unique_tags:
            empty_unique += 1
        values.append(VariableValue(name=Path(image_path).stem, tags=unique_tags))

    filtered_values, conflict_summary = _filter_value_conflicts(values)
    name = (variable_name or folder_path.name).strip()
    variable = Variable(name=name, values=filtered_values)

    stats = {
        "total": len(image_paths),
        "common_count": len(common_tags),
        "empty_unique": empty_unique,
        "common_tags": list(common_tags),
        "removed_conflicts": len(conflict_summary["removed_indices"]),
    }
    return variable, stats


def build_preset(template_name: str, variable: Variable) -> Preset:
    return Preset(name=template_name.strip() or "template", variables=[variable])


def save_preset(path: str | Path, preset: Preset) -> None:
    payload = preset.to_dict()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

