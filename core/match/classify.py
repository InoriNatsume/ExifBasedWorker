from __future__ import annotations

from typing import Iterable

from ..preset.schema import MatchResult, MatchStatus, Variable, VariableMatch


def _normalize_tag(tag: str) -> str:
    return " ".join(tag.split()).strip()


def _normalize_tags(tags: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = _normalize_tag(tag)
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return normalized


def _match_variable(variable: Variable, tag_set: set[str]) -> VariableMatch:
    matched: list[str] = []
    for value in variable.values:
        value_tags = value.tag_set()
        if not value_tags:
            continue
        if value_tags.issubset(tag_set):
            matched.append(value.name)

    if not matched:
        status = MatchStatus.UNKNOWN
    elif len(matched) == 1:
        status = MatchStatus.OK
    else:
        status = MatchStatus.CONFLICT

    return VariableMatch(
        variable_name=variable.name,
        status=status,
        matched_values=matched,
    )


def classify_tags(
    variables: list[Variable],
    tags: Iterable[str],
    image_path: str | None = None,
) -> MatchResult:
    normalized = _normalize_tags(tags)
    tag_set = set(normalized)
    results = [_match_variable(variable, tag_set) for variable in variables]
    return MatchResult(image_path=image_path, variables=results)


def match_tag_and(required_tags: Iterable[str], tags: Iterable[str]) -> bool:
    required_set = set(_normalize_tags(required_tags))
    if not required_set:
        return False
    tag_set = set(_normalize_tags(tags))
    return required_set.issubset(tag_set)
