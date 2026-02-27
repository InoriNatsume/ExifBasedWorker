from __future__ import annotations

from typing import Any

from ..normalize import split_novelai_tags
from ..preset.schema import VariableValue


def _build_value(name: str, prompt: str) -> VariableValue:
    tags = split_novelai_tags(prompt)
    return VariableValue(name=name, tags=tags)


def _scene_name(scene: dict, fallback: str = "Untitled Scene") -> str:
    candidates = (
        scene.get("name"),
        scene.get("scene_name"),
        scene.get("title"),
    )
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return fallback


def _scene_prompt(scene: dict) -> str:
    candidates = (
        scene.get("scenePrompt"),
        scene.get("scene_prompt"),
        scene.get("prompt"),
        scene.get("positivePrompt"),
    )
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    parts: list[str] = []
    for key in ("frontPrompt", "backPrompt"):
        text = str(scene.get(key) or "").strip()
        if text:
            parts.append(text)
    return ", ".join(parts)


def _generate_prompts_from_slots(slots: list[list[dict]]) -> list[str]:
    if not slots:
        return [""]

    first_slot = slots[0] or []
    # NAIS2 최신 로직: enabled가 없으면 활성 상태로 본다.
    enabled_items = [item for item in first_slot if item.get("enabled") is not False]
    rest = _generate_prompts_from_slots(slots[1:])

    if not enabled_items:
        return rest

    results: list[str] = []
    for item in enabled_items:
        current = str(item.get("prompt") or "").strip()
        for tail in rest:
            combined = f"{current}, {tail}" if tail else current
            results.append(combined)
    return results


def _import_legacy_array(payload: list[Any]) -> tuple[str | None, list[VariableValue]]:
    values: list[VariableValue] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        values.append(_build_value(_scene_name(item), _scene_prompt(item)))
    return None, values


def _import_scenes_object(payload: dict[str, Any]) -> tuple[str | None, list[VariableValue]]:
    scenes = payload.get("scenes")
    if not (isinstance(scenes, dict) and scenes):
        return None, []

    values: list[VariableValue] = []
    for scene_data in scenes.values():
        if not isinstance(scene_data, dict):
            continue
        slots = scene_data.get("slots")
        if not isinstance(slots, list):
            continue
        prompts = _generate_prompts_from_slots(slots)
        base_name = _scene_name(scene_data, fallback="Untitled")
        for idx, prompt in enumerate(prompts):
            suffix = f"_{idx + 1}" if len(prompts) > 1 else ""
            values.append(_build_value(f"{base_name}{suffix}", prompt))
    return payload.get("name"), values


def _import_sdstudio_presets(payload: dict[str, Any]) -> tuple[str | None, list[VariableValue]]:
    presets = payload.get("presets")
    if not (isinstance(presets, dict) and isinstance(presets.get("SDImageGenEasy"), list)):
        return None, []

    values: list[VariableValue] = []
    for item in presets.get("SDImageGenEasy") or []:
        if not isinstance(item, dict):
            continue
        values.append(_build_value(_scene_name(item, fallback="Untitled"), _scene_prompt(item)))
    return payload.get("name"), values


def _import_scenes_array(payload: dict[str, Any]) -> tuple[str | None, list[VariableValue]]:
    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        return None, []
    values: list[VariableValue] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        values.append(_build_value(_scene_name(scene, fallback="Untitled"), _scene_prompt(scene)))
    return payload.get("name"), values


def import_scene_preset_payload(payload: Any) -> tuple[str | None, list[VariableValue]]:
    """NAIS2 Scene importPreset 로직(Case A~D) 기준으로 프리셋 JSON을 파싱한다."""
    if isinstance(payload, list):
        return _import_legacy_array(payload)
    if not isinstance(payload, dict):
        raise ValueError("preset payload must be list or dict")

    # Case B: scenes object format
    if payload.get("scenes") and isinstance(payload.get("scenes"), dict):
        name, values = _import_scenes_object(payload)
        if values:
            return name, values

    # Case C: SDImageGenEasy presets
    if payload.get("presets"):
        name, values = _import_sdstudio_presets(payload)
        if values:
            return name, values

    # Case D: standard scenes array format (NAIS/NAIS2)
    name, values = _import_scenes_array(payload)
    if values:
        return name, values

    raise ValueError("지원하지 않는 프리셋 JSON 형식입니다.")
