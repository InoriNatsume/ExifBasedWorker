from __future__ import annotations

from typing import Iterable

from .classify import match_tag_and
from ..extract.tags import extract_tags_from_image


def iter_search_results(
    image_paths: Iterable[str],
    required_tags: Iterable[str],
    include_negative: bool,
) -> Iterable[dict]:
    for path in image_paths:
        try:
            tags = extract_tags_from_image(path, include_negative)
            matched = match_tag_and(required_tags, tags)
            yield {"path": path, "matched": matched, "error": None}
        except Exception as exc:
            yield {"path": path, "matched": False, "error": str(exc)}
