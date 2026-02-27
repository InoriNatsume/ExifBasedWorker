from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.preset import Preset


@dataclass
class AppState:
    preset: Preset
    template_path: str | None = None

    @classmethod
    def create(cls) -> "AppState":
        return cls(preset=Preset(name="default", variables=[]), template_path=None)

    def set_preset(self, preset: Preset, path: str | None = None) -> None:
        self.preset = preset
        self.template_path = path

    def get_template_name(self) -> str:
        if self.preset.name:
            return self.preset.name
        if self.template_path:
            return Path(self.template_path).stem
        return "template"

