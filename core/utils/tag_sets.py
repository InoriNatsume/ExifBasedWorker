from __future__ import annotations

from typing import Iterable

from ..preset.schema import VariableValue


def compute_common_tags(tag_lists: Iterable[Iterable[str]]) -> list[str]:
    lists = [list(tags) for tags in tag_lists]
    if not lists:
        return []

    common_set = set(lists[0])
    for tags in lists[1:]:
        common_set.intersection_update(tags)

    ordered: list[str] = []
    seen: set[str] = set()
    for tag in lists[0]:
        if tag in common_set and tag not in seen:
            ordered.append(tag)
            seen.add(tag)
    return ordered


def remove_common_tags(tag_lists: Iterable[Iterable[str]]) -> tuple[list[list[str]], list[str]]:
    lists = [list(tags) for tags in tag_lists]
    common_tags = compute_common_tags(lists)
    common_set = set(common_tags)
    unique_lists = [
        [tag for tag in tags if tag not in common_set] for tags in lists
    ]
    return unique_lists, common_tags


def remove_common_tags_from_values(
    values: Iterable[VariableValue],
) -> tuple[list[VariableValue], list[str]]:
    values_list = list(values)
    unique_lists, common_tags = remove_common_tags([value.tags for value in values_list])
    updated = [
        VariableValue(name=value.name, tags=unique_lists[idx])
        for idx, value in enumerate(values_list)
    ]
    return updated, common_tags
