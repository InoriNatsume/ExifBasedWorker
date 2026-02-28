from __future__ import annotations

import re
from typing import Any

from .models import Variable, VariableValue


def build_tag_rows(values: list[str]) -> list[dict[str, str]]:
    return [{"value": value, "tag": value} for value in values if value]


def reset_tags_to_values(rows: list[dict[str, str]]) -> None:
    for row in rows:
        row["tag"] = row["value"]


def apply_regex_to_rows(
    rows: list[dict[str, str]],
    pattern_text: str,
    replace_text: str,
    *,
    ignore_case: bool = False,
    source: str = "tag",
) -> int:
    if not pattern_text.strip():
        raise ValueError("정규식을 입력하세요.")

    flags = re.IGNORECASE if ignore_case else 0
    try:
        pattern = re.compile(pattern_text, flags)
    except re.error as exc:
        raise ValueError(f"정규식 오류: {exc}") from exc

    changed = 0
    use_value = source == "value"
    for row in rows:
        base_text = row["value"] if use_value else row["tag"]
        replaced = pattern.sub(replace_text, base_text)
        if row["tag"] != replaced:
            changed += 1
        row["tag"] = replaced
    return changed


def parse_tag_text(tag_text: str) -> list[str]:
    raw_parts = tag_text.replace("\n", ",").split(",")
    return [part.strip() for part in raw_parts if part.strip()]


def build_variable_from_rows(variable_name: str, rows: list[dict[str, str]]) -> Variable:
    name = variable_name.strip() or "character"
    values: list[VariableValue] = []
    for row in rows:
        value_name = row["value"].strip()
        if not value_name:
            continue
        tags = parse_tag_text(row["tag"])
        if not tags:
            raise ValueError(f"값 '{value_name}'의 태그가 비어 있습니다.")
        values.append(VariableValue(name=value_name, tags=tags))

    if not values:
        raise ValueError("저장할 값/태그가 없습니다.")
    return Variable(name=name, values=values)


def build_mapping_payload(
    *,
    template_name: str,
    variable_name: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in rows:
        value_name = row["value"].strip()
        if not value_name:
            continue
        tag_text = row["tag"]
        items.append(
            {
                "value": value_name,
                "tag_text": tag_text,
                "tags": parse_tag_text(tag_text),
            }
        )

    return {
        "template_name": template_name.strip() or "template",
        "variable_name": variable_name.strip() or "character",
        "count": len(items),
        "items": items,
    }
