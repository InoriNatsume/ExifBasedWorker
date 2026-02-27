from __future__ import annotations

from typing import Any

from ..extract.tags import extract_tags_from_image


_VARIABLE_SPECS: list[dict[str, Any]] = []
_INCLUDE_NEGATIVE = False


def _normalize_tag(tag: str) -> str:
    return " ".join(tag.split()).strip()


def _normalize_tags(tags: list[str]) -> set[str]:
    normalized: set[str] = set()
    for tag in tags:
        cleaned = _normalize_tag(tag)
        if cleaned:
            normalized.add(cleaned)
    return normalized


def build_variable_specs(variables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for var in variables:
        values_spec = []
        for value in var.get("values", []):
            tags = value.get("tags") or []
            values_spec.append(
                {
                    "name": value.get("name") or "",
                    "tag_set": _normalize_tags(list(tags)),
                }
            )
        name = var.get("name") or var.get("display_name") or var.get("key") or ""
        specs.append({"name": name, "values": values_spec})
    return specs


def match_variable_specs(
    variable_specs: list[dict[str, Any]],
    tags: list[str],
) -> dict[str, dict[str, Any]]:
    tag_set = _normalize_tags(tags)
    matches: dict[str, dict[str, Any]] = {}
    for spec in variable_specs:
        matched = [
            value["name"]
            for value in spec["values"]
            if value["tag_set"] and value["tag_set"].issubset(tag_set)
        ]
        if not matched:
            status = "UNKNOWN"
        elif len(matched) == 1:
            status = "OK"
        else:
            status = "CONFLICT"
        matches[spec["name"]] = {"status": status, "values": matched}
    return matches


def init_worker(variable_specs: list[dict[str, Any]], include_negative: bool) -> None:
    global _VARIABLE_SPECS, _INCLUDE_NEGATIVE
    _VARIABLE_SPECS = variable_specs
    _INCLUDE_NEGATIVE = include_negative


def process_image(path: str) -> dict[str, Any]:
    try:
        tags = extract_tags_from_image(path, _INCLUDE_NEGATIVE)
        matches = match_variable_specs(_VARIABLE_SPECS, tags)
        return {"path": path, "matches": matches, "error": None}
    except Exception as exc:
        return {"path": path, "matches": {}, "error": str(exc)}
