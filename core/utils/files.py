from __future__ import annotations

import os
from pathlib import Path


def iter_image_files(folder: str | Path) -> list[str]:
    folder_path = Path(folder)
    results: list[str] = []
    for root, _dirs, files in os.walk(folder_path):
        for name in files:
            lower = name.lower()
            if lower.endswith((".png", ".webp", ".jpg", ".jpeg")):
                results.append(str(Path(root) / name))
    return results
