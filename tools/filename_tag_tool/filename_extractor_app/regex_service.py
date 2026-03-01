from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .file_utils import extract_group, iter_image_files


def extract_records_from_folder(
    folder: str,
    pattern_text: str,
    group_spec: str,
    *,
    ignore_case: bool = False,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise ValueError(f"유효한 폴더가 아닙니다: {folder}")

    if not pattern_text.strip():
        raise ValueError("정규식을 입력하세요.")

    flags = re.IGNORECASE if ignore_case else 0
    try:
        pattern = re.compile(pattern_text, flags)
    except re.error as exc:
        raise ValueError(f"정규식 오류: {exc}") from exc

    image_paths = iter_image_files(folder_path)
    if not image_paths:
        return [], {"total": 0, "matched": 0, "unmatched": 0, "empty": 0}

    records: list[dict[str, str]] = []
    matched_count = 0
    unmatched_count = 0
    empty_count = 0

    for image_path in image_paths:
        file_name = Path(image_path).name
        stem = Path(image_path).stem
        match = pattern.search(stem)
        if match is None:
            unmatched_count += 1
            records.append({"path": str(image_path), "file": file_name, "value": "", "status": "NO_MATCH"})
            continue

        try:
            value = extract_group(match, group_spec).strip()
        except Exception as exc:
            raise ValueError(
                "그룹 추출 실패: 그룹 지정이 잘못되었습니다.\n"
                f"입력 그룹: '{group_spec}'\n오류: {exc}"
            ) from exc

        if not value:
            empty_count += 1
            records.append({"path": str(image_path), "file": file_name, "value": "", "status": "EMPTY"})
            continue

        matched_count += 1
        records.append({"path": str(image_path), "file": file_name, "value": value, "status": "OK"})

    return records, {
        "total": len(image_paths),
        "matched": matched_count,
        "unmatched": unmatched_count,
        "empty": empty_count,
    }

