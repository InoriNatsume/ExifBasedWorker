from __future__ import annotations

from typing import Any

from ..normalize import split_novelai_tags
from ..preset.schema import VariableValue


def _build_value(name: str, prompt: str) -> VariableValue:
    tags = split_novelai_tags(prompt)
    return VariableValue(name=name, tags=tags)


def _generate_prompts(slots: list[list[dict]]) -> list[str]:
    if not slots:
        return [""]

    first = slots[0] or []
    enabled = [item for item in first if item.get("enabled")]
    rest = _generate_prompts(slots[1:])

    if not enabled:
        return rest

    results: list[str] = []
    for item in enabled:
        current = item.get("prompt") or ""
        for tail in rest:
            combined = f"{current}, {tail}" if tail else current
            results.append(combined)
    return results


def import_legacy_payload(payload: Any) -> tuple[str | None, list[VariableValue]]:
    if isinstance(payload, list):
        values = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = str(item.get("scene_name") or "Untitled Scene")
            prompt = item.get("scene_prompt") or ""
            values.append(_build_value(name, str(prompt)))
        return None, values

    if not isinstance(payload, dict):
        raise ValueError("legacy payload must be list or dict")

    scenes = payload.get("scenes")
    if isinstance(scenes, dict):
        values = []
        for scene_data in scenes.values():
            if not isinstance(scene_data, dict):
                continue
            slots = scene_data.get("slots")
            if not isinstance(slots, list):
                continue
            prompts = _generate_prompts(slots)
            base_name = str(scene_data.get("name") or "Untitled")
            for idx, prompt in enumerate(prompts):
                suffix = f"_{idx + 1}" if len(prompts) > 1 else ""
                values.append(_build_value(f"{base_name}{suffix}", prompt))
        return payload.get("name"), values

    presets = payload.get("presets")
    if isinstance(presets, dict) and isinstance(presets.get("SDImageGenEasy"), list):
        values = []
        for item in presets.get("SDImageGenEasy"):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "Untitled")
            parts: list[str] = []
            if item.get("frontPrompt"):
                parts.append(str(item.get("frontPrompt")))
            if item.get("backPrompt"):
                parts.append(str(item.get("backPrompt")))
            prompt = ", ".join(parts)
            values.append(_build_value(name, prompt))
        return payload.get("name"), values

    raise ValueError("unknown legacy format")
