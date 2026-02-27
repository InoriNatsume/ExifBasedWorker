import io
import json
import zlib
import gzip
from typing import Any

from PIL import Image, ExifTags
import numpy as np


SIG_ALPHA = b"stealth_pnginfo"
SIG_ALPHA_COMP = b"stealth_pngcomp"


def _decode_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").replace("\x00", "")
    if isinstance(value, str):
        return value.replace("\x00", "")
    return None


def _parse_json_text(text: str | None) -> Any | None:
    if not text:
        return None
    text = text.strip().lstrip("\ufeff")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    # Handle double-encoded JSON strings.
    if isinstance(parsed, str):
        inner = parsed.strip()
        if inner.startswith("{") and inner.endswith("}"):
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                return parsed
    return parsed


def robust_decompress(data_bytes: bytes) -> str | None:
    if data_bytes.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data_bytes)) as handle:
                return handle.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
    try:
        return zlib.decompress(data_bytes).decode("utf-8", errors="ignore")
    except Exception:
        pass
    try:
        return zlib.decompress(data_bytes, -15).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return None


def extract_stealth_payload_text(image_path: str) -> str | None:
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception:
        return None

    arr = np.array(img)
    alpha = arr[:, :, 3]
    alpha_t = alpha.T
    bits = alpha_t.flatten() & 1
    byte_data = np.packbits(bits, bitorder="big")

    header = byte_data[: len(SIG_ALPHA)].tobytes()
    compressed = False
    if header == SIG_ALPHA:
        pass
    elif header == SIG_ALPHA_COMP:
        compressed = True
    else:
        return None

    cursor = len(SIG_ALPHA)
    length_bytes = byte_data[cursor : cursor + 4].tobytes()
    data_len = int.from_bytes(length_bytes, byteorder="big")
    cursor += 4

    payload_byte_len = (data_len + 7) // 8
    payload_bytes = byte_data[cursor : cursor + payload_byte_len].tobytes()

    remainder = data_len % 8
    if remainder != 0:
        last_byte = payload_bytes[-1]
        shifted_byte = last_byte >> (8 - remainder)
        payload_bytes = payload_bytes[:-1] + bytes([shifted_byte])

    if compressed:
        return robust_decompress(payload_bytes)
    return payload_bytes.decode("utf-8", errors="ignore").replace("\x00", "")


def _coerce_payload(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [value]

    text = _decode_text(value)
    if text:
        payload = _parse_json_text(text)
        if isinstance(payload, dict):
            return [payload]
        return [{"prompt": text}]
    return []


_META_KEYS = (
    "Comment",
    "comment",
    "Description",
    "description",
    "UserComment",
    "ImageDescription",
    "XPComment",
    "XPSubject",
    "XPTitle",
)


def unwrap_comment_payload(data: dict) -> list[dict]:
    payloads: list[dict] = []

    for key in _META_KEYS:
        if key in data:
            payloads.extend(_coerce_payload(data.get(key)))

    if payloads:
        return payloads

    if any(key in data for key in ("prompt", "v4_prompt", "raw", "normalized")):
        payloads.append(data)

    return payloads


def extract_payloads_from_metadata(metadata: dict) -> list[dict]:
    return unwrap_comment_payload(metadata)


def _decode_exif_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        text = _decode_text(value)
        if text:
            return text
        try:
            return value.decode("utf-16le", errors="ignore").replace("\x00", "")
        except Exception:
            return None
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, tuple):
        try:
            raw = bytes(value)
        except Exception:
            return None
        try:
            return raw.decode("utf-16le", errors="ignore").replace("\x00", "")
        except Exception:
            return _decode_text(raw)
    return None


def extract_payloads_from_exif(img: Image.Image) -> list[dict]:
    try:
        exif = img.getexif()
    except Exception:
        return []
    if not exif:
        return []
    exif_map: dict[str, Any] = {}
    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        text = _decode_exif_value(value)
        if text is not None:
            exif_map[tag_name] = text
    if not exif_map:
        return []
    return unwrap_comment_payload(exif_map)


def extract_payloads_from_image(image_path: str) -> list[dict]:
    payloads: list[dict] = []
    raw_payloads: list[dict] = []

    stealth_text = extract_stealth_payload_text(image_path)
    if stealth_text:
        stealth_payload = _parse_json_text(stealth_text)
        if isinstance(stealth_payload, dict):
            raw_payloads.append(stealth_payload)

    try:
        with Image.open(image_path) as img:
            exif_payloads = extract_payloads_from_exif(img)
            info_payloads = extract_payloads_from_metadata(img.info or {})
            raw_payloads.extend(exif_payloads)
            raw_payloads.extend(info_payloads)
    except Exception:
        return payloads

    for item in raw_payloads:
        if isinstance(item, dict) and any(key in item for key in _META_KEYS):
            expanded = unwrap_comment_payload(item)
            if expanded:
                payloads.extend(expanded)
                continue
        payloads.append(item)

    return payloads
