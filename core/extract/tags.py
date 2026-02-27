from __future__ import annotations

from typing import Iterable

from .payload import extract_payloads_from_image
from ..normalize.novelai import merge_prompt_tags, normalize_novelai_payload


def _dedupe(tags: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        result.append(tag)
    return result


def extract_tags_from_payload(payload: dict, include_negative: bool) -> list[str]:
    normalized = normalize_novelai_payload(payload)
    tags = merge_prompt_tags(normalized, include_negative=include_negative)
    return _dedupe(tags)


def extract_tags_from_image(image_path: str, include_negative: bool) -> list[str]:
    payloads = extract_payloads_from_image(image_path)
    combined: list[str] = []
    for payload in payloads:
        combined.extend(extract_tags_from_payload(payload, include_negative))
    return _dedupe(combined)
