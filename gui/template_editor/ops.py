from __future__ import annotations

from core.normalize import split_novelai_tags
from core.preset import Preset

from .validation import validate_value_tag_constraints


def normalize_tags_input(tags_text: str) -> list[str]:
    return split_novelai_tags(tags_text)


def add_variable(preset: Preset, variable_name: str) -> Preset:
    name = variable_name.strip()
    if not name:
        raise ValueError("변수 이름이 비어 있습니다.")
    payload = preset.model_dump()
    payload.setdefault("variables", [])
    if any(item.get("name") == name for item in payload["variables"]):
        raise ValueError(f"이미 존재하는 변수입니다: {name}")
    payload["variables"].append({"name": name, "values": []})
    return Preset.model_validate(payload)


def rename_variable(preset: Preset, var_index: int, new_name: str) -> Preset:
    name = new_name.strip()
    if not name:
        raise ValueError("변수 이름이 비어 있습니다.")
    payload = preset.model_dump()
    variables = payload.get("variables", [])
    if var_index < 0 or var_index >= len(variables):
        raise ValueError("유효하지 않은 변수 인덱스입니다.")

    for idx, item in enumerate(variables):
        if idx != var_index and item.get("name") == name:
            raise ValueError(f"이미 존재하는 변수입니다: {name}")
    variables[var_index]["name"] = name
    return Preset.model_validate(payload)


def delete_variable(preset: Preset, var_index: int) -> Preset:
    payload = preset.model_dump()
    variables = payload.get("variables", [])
    if var_index < 0 or var_index >= len(variables):
        raise ValueError("유효하지 않은 변수 인덱스입니다.")
    variables.pop(var_index)
    return Preset.model_validate(payload)


def add_value(
    preset: Preset,
    var_index: int,
    value_name: str,
    tags: list[str],
) -> Preset:
    name = value_name.strip()
    if not name:
        raise ValueError("값 이름이 비어 있습니다.")
    payload = preset.model_dump()
    variables = payload.get("variables", [])
    if var_index < 0 or var_index >= len(variables):
        raise ValueError("유효하지 않은 변수 인덱스입니다.")

    values = variables[var_index].setdefault("values", [])
    if any(item.get("name") == name for item in values):
        raise ValueError(f"이미 존재하는 값입니다: {name}")
    values.append({"name": name, "tags": tags})
    validate_value_tag_constraints(values)
    return Preset.model_validate(payload)


def update_value(
    preset: Preset,
    var_index: int,
    value_index: int,
    value_name: str,
    tags: list[str],
) -> Preset:
    name = value_name.strip()
    if not name:
        raise ValueError("값 이름이 비어 있습니다.")
    payload = preset.model_dump()
    variables = payload.get("variables", [])
    if var_index < 0 or var_index >= len(variables):
        raise ValueError("유효하지 않은 변수 인덱스입니다.")

    values = variables[var_index].setdefault("values", [])
    if value_index < 0 or value_index >= len(values):
        raise ValueError("유효하지 않은 값 인덱스입니다.")

    for idx, item in enumerate(values):
        if idx != value_index and item.get("name") == name:
            raise ValueError(f"이미 존재하는 값입니다: {name}")
    values[value_index] = {"name": name, "tags": tags}
    validate_value_tag_constraints(values)
    return Preset.model_validate(payload)


def delete_value(preset: Preset, var_index: int, value_index: int) -> Preset:
    payload = preset.model_dump()
    variables = payload.get("variables", [])
    if var_index < 0 or var_index >= len(variables):
        raise ValueError("유효하지 않은 변수 인덱스입니다.")
    values = variables[var_index].setdefault("values", [])
    if value_index < 0 or value_index >= len(values):
        raise ValueError("유효하지 않은 값 인덱스입니다.")
    values.pop(value_index)
    return Preset.model_validate(payload)
