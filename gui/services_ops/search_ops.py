from __future__ import annotations

import logging

from core.match import match_tag_and
from core.normalize import split_novelai_tags
from core.utils import iter_image_files

from .common import CancelCallback, ProgressCallback, get_tags_cached

_logger = logging.getLogger(__name__)


def search_images(
    folder: str,
    tags_input: str,
    *,
    include_negative: bool = False,
    progress_cb: ProgressCallback | None = None,
    cancel_cb: CancelCallback | None = None,
) -> list[dict]:
    required_tags = split_novelai_tags(tags_input)
    if not required_tags:
        raise ValueError("검색 태그가 비어 있습니다.")

    image_paths = iter_image_files(folder)
    total = len(image_paths)
    results: list[dict] = []
    cache_hits = 0
    cache_misses = 0
    for idx, path in enumerate(image_paths, start=1):
        if cancel_cb and cancel_cb():
            break
        try:
            tags, cache_status = get_tags_cached(path, include_negative)
            if cache_status is True:
                cache_hits += 1
            elif cache_status is False:
                cache_misses += 1

            if match_tag_and(required_tags, tags):
                results.append(
                    {
                        "status": "OK",
                        "source": path,
                        "target": None,
                        "message": None,
                        "preview": path,
                    }
                )
        except Exception as exc:
            results.append(
                {
                    "status": "ERROR",
                    "source": path,
                    "target": None,
                    "message": str(exc),
                    "preview": path,
                }
            )
        if progress_cb:
            progress_cb(idx, total)
    _logger.info("search cache: hit=%d miss=%d total=%d", cache_hits, cache_misses, total)
    return results
