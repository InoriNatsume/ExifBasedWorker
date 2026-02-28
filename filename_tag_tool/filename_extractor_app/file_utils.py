from __future__ import annotations

import os
from pathlib import Path
import re


_IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg")


def iter_image_files(folder: str | Path) -> list[str]:
    folder_path = Path(folder)
    results: list[str] = []
    for root, _dirs, files in os.walk(folder_path):
        for name in files:
            if name.lower().endswith(_IMAGE_EXTS):
                results.append(str(Path(root) / name))
    results.sort()
    return results


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def extract_group(match: re.Match[str], group_spec: str) -> str:
    spec = group_spec.strip()
    if not spec:
        return str(match.group(0))
    if spec.isdigit():
        return str(match.group(int(spec)))
    return str(match.group(spec))


def compute_common_tags(tag_lists: list[list[str]]) -> list[str]:
    if not tag_lists:
        return []

    common_set = set(tag_lists[0])
    for tags in tag_lists[1:]:
        common_set.intersection_update(tags)

    ordered: list[str] = []
    seen: set[str] = set()
    for tag in tag_lists[0]:
        if tag in common_set and tag not in seen:
            ordered.append(tag)
            seen.add(tag)
    return ordered


def remove_common_tags(tag_lists: list[list[str]]) -> tuple[list[list[str]], list[str]]:
    common_tags = compute_common_tags(tag_lists)
    common_set = set(common_tags)
    unique_lists = [[tag for tag in tags if tag not in common_set] for tags in tag_lists]
    return unique_lists, common_tags

