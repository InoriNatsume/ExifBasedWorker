from __future__ import annotations

import re

from core.preset import Preset


_SPACE_RE = re.compile(r"\s+")


def _normalize_tag(tag: str) -> str:
    return _SPACE_RE.sub(" ", str(tag)).strip()


def _normalized_tag_set(tags: list[str]) -> frozenset[str]:
    normalized: set[str] = set()
    for raw in tags:
        cleaned = _normalize_tag(raw)
        if cleaned:
            normalized.add(cleaned)
    return frozenset(normalized)


def validate_value_tag_constraints(values: list[dict[str, object]]) -> None:
    # core.preset.schema 의 규칙(중복/부분집합 금지)을 UI 단계에서 한국어로 먼저 안내한다.
    entries: list[tuple[str, frozenset[str]]] = []
    for item in values:
        name = str(item.get("name") or "").strip()
        raw_tags = item.get("tags") or []
        tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
        tag_set = _normalized_tag_set(tags)
        if tag_set:
            entries.append((name, tag_set))

    seen: dict[frozenset[str], str] = {}
    for name, tag_set in entries:
        other = seen.get(tag_set)
        if other is not None:
            raise ValueError(f"태그 조합이 중복됩니다: '{name}' 와 '{other}'")
        seen[tag_set] = name

    sorted_entries = sorted(entries, key=lambda item: len(item[1]))
    for idx, (name_a, set_a) in enumerate(sorted_entries):
        for name_b, set_b in sorted_entries[idx + 1 :]:
            if set_a.issubset(set_b):
                raise ValueError(f"태그 부분집합 충돌: '{name_a}' ⊂ '{name_b}'")


def validate_preset_for_ui(preset: Preset) -> None:
    payload = preset.model_dump()
    variables = payload.get("variables", [])
    empty_tag_values: list[str] = []

    seen_variables: set[str] = set()
    for var_idx, variable in enumerate(variables, start=1):
        variable_name = str(variable.get("name") or "").strip()
        if not variable_name:
            raise ValueError(f"{var_idx}번째 변수 이름이 비어 있습니다.")
        if variable_name in seen_variables:
            raise ValueError(f"변수 이름 중복: '{variable_name}'")
        seen_variables.add(variable_name)

        values = variable.get("values") or []
        seen_values: set[str] = set()
        for value_idx, value in enumerate(values, start=1):
            value_name = str(value.get("name") or "").strip()
            if not value_name:
                raise ValueError(
                    f"변수 '{variable_name}'의 {value_idx}번째 값 이름이 비어 있습니다."
                )
            if value_name in seen_values:
                raise ValueError(
                    f"변수 '{variable_name}'에서 값 이름이 중복됩니다: '{value_name}'"
                )
            seen_values.add(value_name)
            raw_tags = value.get("tags") or []
            tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
            if not _normalized_tag_set(tags):
                empty_tag_values.append(f"{variable_name}/{value_name}")

        validate_value_tag_constraints(values)

    if empty_tag_values:
        preview = ", ".join(empty_tag_values[:10])
        remain = len(empty_tag_values) - 10
        if remain > 0:
            preview = f"{preview} 외 {remain}개"
        raise ValueError(f"태그가 비어 있는 값이 있습니다: {preview}")

    try:
        Preset.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"템플릿 스키마 오류: {exc}") from exc
