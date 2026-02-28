from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VariableValue:
    name: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tags": list(self.tags),
        }


@dataclass
class Variable:
    name: str
    values: list[VariableValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "values": [value.to_dict() for value in self.values],
        }


@dataclass
class Preset:
    name: str | None = None
    variables: list[Variable] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "variables": [variable.to_dict() for variable in self.variables],
        }

