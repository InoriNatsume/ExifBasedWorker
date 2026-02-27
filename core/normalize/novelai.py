import re
from typing import Iterable

from .schema import parse_novelai_payload


_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _is_number(text: str) -> bool:
    return bool(_NUMBER_RE.fullmatch(text))


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_novelai_tags(text: str | None) -> list[str]:
    if not text:
        return []

    cleaned = text.replace("::", ",").replace("\n", ",")
    raw_parts = [part.strip() for part in cleaned.split(",")]
    tags: list[str] = []

    for part in raw_parts:
        if not part:
            continue

        part = part.replace("{", "").replace("}", "")
        part = part.replace("[", "").replace("]", "")
        part = part.strip()

        if not part:
            continue

        if part.startswith("||") and part.endswith("||") and len(part) > 4:
            part = part[2:-2].strip()

        part = part.strip("|")

        if not part:
            continue

        if "|" in part:
            for sub in part.split("|"):
                _add_tag(tags, sub)
            continue

        _add_tag(tags, part)

    return tags


def _add_tag(tags: list[str], raw: str) -> None:
    tag = _collapse_spaces(raw)
    if not tag or _is_number(tag):
        return
    tags.append(tag)


def normalize_novelai_payload(data: dict) -> dict:
    parsed = parse_novelai_payload(data)
    out: dict = {
        "vendor": parsed.vendor,
        "source": parsed.source,
        "prompt_tags": split_novelai_tags(parsed.prompt),
        "negative_prompt_tags": split_novelai_tags(parsed.negative_prompt),
    }

    if parsed.char_prompts:
        char_prompts = []
        for item in parsed.char_prompts:
            tags = split_novelai_tags(item.caption)
            if tags:
                char_prompts.append({"idx": item.idx, "tags": tags})
        if char_prompts:
            out["char_prompt_tags"] = char_prompts

    if parsed.char_negative_prompts:
        char_neg_prompts = []
        for item in parsed.char_negative_prompts:
            tags = split_novelai_tags(item.caption)
            if tags:
                char_neg_prompts.append({"idx": item.idx, "tags": tags})
        if char_neg_prompts:
            out["char_negative_prompt_tags"] = char_neg_prompts

    return out


def merge_prompt_tags(normalized: dict, include_negative: bool) -> list[str]:
    tags: list[str] = []
    tags.extend(normalized.get("prompt_tags", []))

    for item in normalized.get("char_prompt_tags", []) or []:
        if isinstance(item, dict):
            tags.extend(item.get("tags", []) or [])

    if include_negative:
        tags.extend(normalized.get("negative_prompt_tags", []))
        for item in normalized.get("char_negative_prompt_tags", []) or []:
            if isinstance(item, dict):
                tags.extend(item.get("tags", []) or [])

    return tags
