from __future__ import annotations

from enum import Enum
import re
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SPACE_RE = re.compile(r"\s+")


def _normalize_tag(tag: str) -> str:
    cleaned = _SPACE_RE.sub(" ", tag).strip()
    return cleaned


def _normalize_tags(tags: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        cleaned = _normalize_tag(raw)
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return normalized


class MatchStatus(str, Enum):
    OK = "OK"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class VariableValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value name must not be empty")
        return cleaned

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Iterable[str] | None) -> list[str]:
        if value is None:
            return []
        return list(value)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value)

    def tag_set(self) -> frozenset[str]:
        return frozenset(self.tags)


class Variable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    values: list[VariableValue] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_labels(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        name = data.get("name")
        legacy_name = data.get("display_name") or data.get("key")
        if name and legacy_name and str(name).strip() != str(legacy_name).strip():
            raise ValueError("variable name mismatch between name/display_name/key")
        if not name and legacy_name:
            data["name"] = legacy_name
        data.pop("display_name", None)
        data.pop("key", None)
        return data

    @field_validator("name")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("variable name must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _validate_value_sets(self) -> "Variable":
        tag_sets: dict[frozenset[str], str] = {}
        entries: list[tuple[str, frozenset[str]]] = []

        for item in self.values:
            tag_set = item.tag_set()
            if not tag_set:
                continue
            if tag_set in tag_sets:
                raise ValueError(
                    f"duplicate tag sets: '{item.name}' and '{tag_sets[tag_set]}'"
                )
            tag_sets[tag_set] = item.name
            entries.append((item.name, tag_set))

        entries.sort(key=lambda entry: len(entry[1]))
        for idx, (name_a, set_a) in enumerate(entries):
            for name_b, set_b in entries[idx + 1 :]:
                if set_a.issubset(set_b):
                    raise ValueError(
                        f"subset tag sets are not allowed: '{name_a}' subset of '{name_b}'"
                    )

        return self


class Preset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    variables: list[Variable] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _drop_legacy_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            data.pop("output_template", None)
        return data

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def _validate_variable_names(self) -> "Preset":
        seen: set[str] = set()
        for var in self.variables:
            name = var.name
            if name in seen:
                raise ValueError(f"duplicate variable name: '{name}'")
            seen.add(name)
        return self


class VariableMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_name: str
    status: MatchStatus
    matched_values: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_path: str | None = None
    variables: list[VariableMatch] = Field(default_factory=list)


RuleSet = Preset
