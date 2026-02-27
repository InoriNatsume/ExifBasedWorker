from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..preset.schema import VariableValue


@dataclass(frozen=True)
class ConflictSummary:
    duplicate_pairs: list[tuple[int, int]]
    subset_pairs: list[tuple[int, int]]
    removed_indices: set[int]

    @property
    def has_conflicts(self) -> bool:
        return bool(self.duplicate_pairs or self.subset_pairs)


def detect_value_conflicts(values: Iterable[VariableValue]) -> ConflictSummary:
    values_list = list(values)
    tag_sets: dict[frozenset[str], int] = {}
    entries: list[tuple[int, frozenset[str]]] = []
    duplicate_pairs: list[tuple[int, int]] = []
    duplicate_indices: set[int] = set()

    for idx, value in enumerate(values_list):
        tag_set = value.tag_set()
        if not tag_set:
            continue
        if tag_set in tag_sets:
            other_idx = tag_sets[tag_set]
            duplicate_pairs.append((idx, other_idx))
            duplicate_indices.add(idx)
            continue
        tag_sets[tag_set] = idx
        entries.append((idx, tag_set))

    entries.sort(key=lambda item: len(item[1]))
    subset_pairs: list[tuple[int, int]] = []
    subset_indices: set[int] = set()

    for pos, (idx, set_a) in enumerate(entries):
        for other_idx, set_b in entries[pos + 1 :]:
            if set_a.issubset(set_b):
                subset_pairs.append((idx, other_idx))
                subset_indices.add(idx)
                break

    removed_indices = duplicate_indices | subset_indices
    return ConflictSummary(
        duplicate_pairs=duplicate_pairs,
        subset_pairs=subset_pairs,
        removed_indices=removed_indices,
    )


def filter_value_conflicts(
    values: Iterable[VariableValue],
) -> tuple[list[VariableValue], ConflictSummary]:
    values_list = list(values)
    summary = detect_value_conflicts(values_list)
    if not summary.has_conflicts:
        return values_list, summary

    filtered = [
        value for idx, value in enumerate(values_list) if idx not in summary.removed_indices
    ]
    return filtered, summary
