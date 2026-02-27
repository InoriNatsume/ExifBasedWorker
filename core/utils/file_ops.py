from __future__ import annotations

from pathlib import Path


_INVALID_CHARS = '<>:"/\\|?*'
_INVALID_TRANS = str.maketrans({ch: "_" for ch in _INVALID_CHARS})


def sanitize_filename(name: str, fallback: str = "unnamed") -> str:
    cleaned = name.translate(_INVALID_TRANS).strip()
    cleaned = cleaned.strip(". ")
    if not cleaned:
        return fallback
    return cleaned


def render_template(template: str, mapping: dict[str, str]) -> str:
    result = template
    for key, value in mapping.items():
        result = result.replace(f"[{key}]", value)
    return result.strip()


def ensure_unique_name(
    folder: str | Path,
    base_name: str,
    extension: str,
    reserved: set[str],
) -> str:
    base = sanitize_filename(base_name)
    ext = extension if extension.startswith(".") or extension == "" else f".{extension}"
    candidate = f"{base}{ext}"
    candidate_lower = candidate.lower()
    folder_path = Path(folder)

    if candidate_lower not in reserved and not (folder_path / candidate).exists():
        reserved.add(candidate_lower)
        return candidate

    index = 1
    while True:
        candidate = f"{base}@@@{index}{ext}"
        candidate_lower = candidate.lower()
        if candidate_lower not in reserved and not (folder_path / candidate).exists():
            reserved.add(candidate_lower)
            return candidate
        index += 1
