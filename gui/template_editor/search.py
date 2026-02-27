from __future__ import annotations

from core.preset import Variable


def build_value_candidates(variable: Variable) -> list[str]:
    return [value.name for value in variable.values]


def build_tag_candidates(variable: Variable) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for value in variable.values:
        for tag in value.tags:
            if tag in seen:
                continue
            seen.add(tag)
            candidates.append(tag)
    candidates.sort(key=str.casefold)
    return candidates


def filter_suggestions(
    candidates: list[str],
    query: str,
    *,
    csv_mode: bool = False,
    limit: int = 300,
) -> list[str]:
    if csv_mode:
        token = query.rsplit(",", 1)[-1].strip().casefold()
    else:
        token = query.strip().casefold()
    if token:
        values = [item for item in candidates if token in item.casefold()]
    else:
        values = list(candidates)
    if len(values) > limit:
        return values[:limit]
    return values


def find_best_value_match_index(items: list[str], query: str) -> int:
    query_lower = query.strip().casefold()
    if not query_lower:
        return -1

    exact_idx = -1
    partial_idx = -1
    for idx, item in enumerate(items):
        item_lower = item.casefold()
        if item_lower == query_lower:
            exact_idx = idx
            break
        if partial_idx < 0 and query_lower in item_lower:
            partial_idx = idx

    return exact_idx if exact_idx >= 0 else partial_idx


def find_tag_match_indices(tags: list[str], queries: list[str]) -> list[int]:
    wanted = [item.casefold() for item in queries]
    matched: list[int] = []
    for idx, tag in enumerate(tags):
        tag_lower = tag.casefold()
        if any(query in tag_lower for query in wanted):
            matched.append(idx)
    return matched
