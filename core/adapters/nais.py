from __future__ import annotations

from ..normalize import split_novelai_tags
from ..preset.schema import VariableValue


def import_nais_payload(payload: dict) -> tuple[str | None, list[VariableValue]]:
    if not isinstance(payload, dict):
        raise ValueError("NAIS payload must be a dict")

    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("NAIS payload missing scenes list")

    values: list[VariableValue] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        name = str(scene.get("name") or "Untitled")
        prompt = scene.get("scenePrompt") or ""
        if not isinstance(prompt, str):
            prompt = str(prompt)
        tags = split_novelai_tags(prompt)
        values.append(VariableValue(name=name, tags=tags))

    return payload.get("name"), values
