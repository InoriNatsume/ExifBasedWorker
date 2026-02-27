from __future__ import annotations

import json
from pathlib import Path

from .schema import Preset


def load_preset(path: str | Path) -> Preset:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return Preset.model_validate(payload)


def save_preset(path: str | Path, preset: Preset) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(preset.model_dump(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
