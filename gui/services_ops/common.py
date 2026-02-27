from __future__ import annotations

from collections import OrderedDict
import os
from pathlib import Path
import threading
from typing import Callable

from core.extract import extract_tags_from_image as _core_extract_tags_from_image
from core.preset import Preset
from core.utils import sanitize_filename

ProgressCallback = Callable[[int, int], None]
CancelCallback = Callable[[], bool]

_TAG_CACHE_MAX = 10000
_TAG_CACHE_LOCK = threading.Lock()
_TAG_CACHE: OrderedDict[tuple[str, int, int, bool], list[str]] = OrderedDict()


def tag_cache_key(path: str, include_negative: bool) -> tuple[str, int, int, bool] | None:
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (os.path.abspath(path), int(stat.st_size), int(stat.st_mtime_ns), include_negative)


def get_tags_cached(path: str, include_negative: bool) -> tuple[list[str], bool | None]:
    key = tag_cache_key(path, include_negative)
    if key is not None:
        with _TAG_CACHE_LOCK:
            cached = _TAG_CACHE.get(key)
            if cached is not None:
                _TAG_CACHE.move_to_end(key)
                return list(cached), True

    tags = _resolve_extract_tags_fn()(path, include_negative)

    if key is not None:
        with _TAG_CACHE_LOCK:
            _TAG_CACHE[key] = list(tags)
            _TAG_CACHE.move_to_end(key)
            while len(_TAG_CACHE) > _TAG_CACHE_MAX:
                _TAG_CACHE.popitem(last=False)
        return tags, False
    return tags, None


def _resolve_extract_tags_fn():
    try:
        # 테스트에서 기존 경로(gui.services.extract_tags_from_image)를 패치하는 경우를 호환한다.
        from .. import services as services_module

        return getattr(services_module, "extract_tags_from_image", _core_extract_tags_from_image)
    except Exception:
        return _core_extract_tags_from_image


def normalize_match_tag(tag: str) -> str:
    return " ".join(tag.replace("_", " ").split()).strip()


def normalized_tag_set(tags: list[str]) -> set[str]:
    normalized: set[str] = set()
    for item in tags:
        cleaned = normalize_match_tag(item)
        if cleaned:
            normalized.add(cleaned)
    return normalized


def build_variable_value_specs(variable_spec: dict) -> list[tuple[str, set[str]]]:
    out: list[tuple[str, set[str]]] = []
    for item in variable_spec.get("values", []) or []:
        name = str(item.get("name") or "")
        tag_set = set(item.get("tag_set") or set())
        if name and tag_set:
            out.append((name, tag_set))
    return out


def sanitize_folder_template_path(path_text: str) -> str:
    raw = str(path_text or "").strip()
    if not raw:
        return ""
    normalized = raw.replace("\\", "/").strip().strip("/")
    if not normalized:
        return ""
    parts: list[str] = []
    for part in normalized.split("/"):
        segment = sanitize_filename(part.strip(), fallback="").strip()
        if segment:
            parts.append(segment)
    if not parts:
        return ""
    return str(Path(*parts))


def explain_unknown_match(
    variable_name: str,
    value_specs: list[tuple[str, set[str]]],
    image_tags: list[str],
) -> str:
    if not value_specs:
        return f"변수 '{variable_name}'에 매칭 태그가 없습니다."

    image_tag_set = normalized_tag_set(image_tags)
    if not image_tag_set:
        return "이미지에서 태그를 추출하지 못했습니다."

    best_name = ""
    best_overlap = 0
    best_required_count = 0
    best_missing: set[str] = set()

    for name, required in value_specs:
        overlap = len(required & image_tag_set)
        if overlap > best_overlap:
            best_overlap = overlap
            best_name = name
            best_required_count = len(required)
            best_missing = required - image_tag_set

    if best_overlap <= 0:
        return "템플릿 태그와 일치하는 항목이 없습니다."

    missing_preview = ", ".join(sorted(best_missing)[:4])
    if missing_preview:
        return (
            f"가까운 값 '{best_name}' 매치 {best_overlap}/{best_required_count}, "
            f"누락 태그: {missing_preview}"
        )
    return f"가까운 값 '{best_name}' 매치 {best_overlap}/{best_required_count}"


def template_to_variables_payload(preset: Preset) -> list[dict]:
    return [
        {
            "name": var.name,
            "values": [{"name": value.name, "tags": list(value.tags)} for value in var.values],
        }
        for var in preset.variables
    ]
