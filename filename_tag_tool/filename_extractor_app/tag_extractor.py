from __future__ import annotations

import json
import re
from typing import Any

from PIL import ExifTags, Image


_SPACE_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _is_number(text: str) -> bool:
    return bool(_NUMBER_RE.fullmatch(text))


def _collapse_spaces(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip()


def _decode_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16", "utf-16le", "utf-16be", "latin1"):
            try:
                return value.decode(encoding, errors="ignore")
            except Exception:
                continue
        return value.decode("utf-8", errors="ignore")
    return str(value)


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
                _append_tag(tags, sub)
            continue
        _append_tag(tags, part)
    return tags


def _append_tag(tags: list[str], raw: str) -> None:
    tag = _collapse_spaces(raw)
    if not tag or _is_number(tag):
        return
    tags.append(tag)


def _parse_json_text(text: str | None) -> Any | None:
    if not text:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, str):
        inner = parsed.strip()
        if inner.startswith("{") or inner.startswith("["):
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                return parsed
    return parsed


def _iter_info_texts(info: dict[str, Any]) -> list[str]:
    keys = (
        "Comment",
        "comment",
        "Description",
        "description",
        "parameters",
        "Parameters",
        "prompt",
        "Prompt",
        "Software",
        "UserComment",
    )
    texts: list[str] = []
    for key in keys:
        decoded = _decode_text(info.get(key))
        if decoded:
            texts.append(decoded)
    for value in info.values():
        decoded = _decode_text(value)
        if decoded and decoded not in texts:
            texts.append(decoded)
    return texts


def _iter_exif_texts(image: Image.Image) -> list[str]:
    texts: list[str] = []
    try:
        exif = image.getexif()
    except Exception:
        exif = None
    if not exif:
        return texts
    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        decoded = _decode_text(value)
        if not decoded:
            continue
        if tag_name in ("UserComment", "ImageDescription", "XPComment", "XPTitle"):
            texts.append(decoded)
        elif decoded.startswith("{") or decoded.startswith("["):
            texts.append(decoded)
    return texts


def _payload_source(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("normalized"), dict):
        return payload["normalized"]
    if isinstance(payload.get("raw"), dict):
        return payload["raw"]
    return payload


def _pick_first_text(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = data.get(key)
        text = _decode_text(value)
        if text and text.strip():
            return text.strip()
    return ""


def _extract_v4_caption_text(block: Any) -> str:
    if not isinstance(block, dict):
        return ""
    caption = block.get("caption")
    if isinstance(caption, dict):
        base = _decode_text(caption.get("base_caption"))
        if base and base.strip():
            return base.strip()
    return ""


def _extract_char_caption_texts(block: Any) -> list[str]:
    texts: list[str] = []
    if not isinstance(block, list):
        return texts
    for item in block:
        if not isinstance(item, dict):
            continue
        text = _pick_first_text(item, ("char_caption", "caption"))
        if text:
            texts.append(text)
    return texts


def _extract_payload_prompts(payload: dict[str, Any]) -> tuple[str, str, list[str], list[str]]:
    src = _payload_source(payload)

    prompt = _pick_first_text(src, ("prompt", "positive_prompt", "scenePrompt", "scene_prompt"))
    negative = _pick_first_text(src, ("negative_prompt", "uc"))

    params = src.get("params")
    if isinstance(params, dict):
        if not prompt:
            prompt = _pick_first_text(params, ("prompt",))
        if not negative:
            negative = _pick_first_text(params, ("negative_prompt", "uc"))

    if not prompt:
        prompt = _extract_v4_caption_text(src.get("v4_prompt"))
    if not negative:
        negative = _extract_v4_caption_text(src.get("v4_negative_prompt"))

    char_prompts = _extract_char_caption_texts(src.get("char_prompts"))
    char_negative_prompts = _extract_char_caption_texts(src.get("char_negative_prompts"))

    v4_prompt = src.get("v4_prompt")
    if not char_prompts and isinstance(v4_prompt, dict):
        caption = v4_prompt.get("caption")
        if isinstance(caption, dict):
            char_prompts = _extract_char_caption_texts(caption.get("char_captions"))

    v4_negative_prompt = src.get("v4_negative_prompt")
    if not char_negative_prompts and isinstance(v4_negative_prompt, dict):
        caption = v4_negative_prompt.get("caption")
        if isinstance(caption, dict):
            char_negative_prompts = _extract_char_caption_texts(caption.get("char_captions"))

    return prompt, negative, char_prompts, char_negative_prompts


def extract_tags_from_payload(payload: dict[str, Any], include_negative: bool) -> list[str]:
    prompt, negative, char_prompts, char_negative_prompts = _extract_payload_prompts(payload)
    tags: list[str] = []
    tags.extend(split_novelai_tags(prompt))
    for item in char_prompts:
        tags.extend(split_novelai_tags(item))
    if include_negative:
        tags.extend(split_novelai_tags(negative))
        for item in char_negative_prompts:
            tags.extend(split_novelai_tags(item))
    return tags


def _extract_tags_from_plain_text(text: str, include_negative: bool) -> list[str]:
    data = text.strip()
    if not data:
        return []
    prompt = data
    negative = ""
    marker = "Negative prompt:"
    idx = data.find(marker)
    if idx >= 0:
        prompt = data[:idx]
        tail = data[idx + len(marker) :]
        split_idx = tail.find("\nSteps:")
        if split_idx >= 0:
            negative = tail[:split_idx]
        else:
            negative = tail
    tags = split_novelai_tags(prompt)
    if include_negative:
        tags.extend(split_novelai_tags(negative))
    return tags


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def extract_tags_from_image(image_path: str, include_negative: bool) -> list[str]:
    raw_texts: list[str] = []
    try:
        with Image.open(image_path) as image:
            raw_texts.extend(_iter_info_texts(image.info or {}))
            raw_texts.extend(_iter_exif_texts(image))
    except Exception:
        return []

    payloads: list[dict[str, Any]] = []
    plain_texts: list[str] = []
    for text in raw_texts:
        parsed = _parse_json_text(text)
        if isinstance(parsed, dict):
            payloads.append(parsed)
            continue
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    payloads.append(item)
            continue
        plain_texts.append(text)

    tags: list[str] = []
    for payload in payloads:
        tags.extend(extract_tags_from_payload(payload, include_negative))

    # JSON payload을 못 찾은 경우 plain text 파싱을 시도한다.
    if not tags:
        for text in plain_texts:
            tags.extend(_extract_tags_from_plain_text(text, include_negative))

    return _dedupe_keep_order(tags)

