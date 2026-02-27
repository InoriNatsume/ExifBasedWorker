from __future__ import annotations

import json
from pathlib import Path

from core.adapters.folder_builder import build_nais_from_folder
from core.adapters.nais import import_nais_payload
from core.adapters.scene_preset import import_scene_preset_payload
from core.match import filter_value_conflicts
from core.preset import Variable

from .common import ProgressCallback


def build_variable_from_folder(
    folder: str,
    *,
    variable_name: str | None = None,
    include_negative: bool = False,
    progress_cb: ProgressCallback | None = None,
) -> tuple[Variable, dict]:
    payload, stats = build_nais_from_folder(
        folder,
        include_negative=include_negative,
        progress_step=100,
        progress_cb=progress_cb,
    )
    auto_name, values = import_nais_payload(payload)
    filtered_values, summary = filter_value_conflicts(values)
    name = (variable_name or auto_name or Path(folder).name).strip()
    variable = Variable(name=name, values=filtered_values)
    out_stats = dict(stats)
    out_stats["removed_conflicts"] = len(summary.removed_indices)
    return variable, out_stats


def build_variable_from_preset_json(
    preset_json_path: str | Path,
    *,
    variable_name: str | None = None,
) -> tuple[Variable, dict]:
    path = Path(preset_json_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"JSON 파일이 없습니다: {path}")

    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise ValueError(f"JSON 로드 실패: {exc}") from exc

    auto_name, values = import_scene_preset_payload(payload)

    filtered_non_empty = [value for value in values if value.tags]
    removed_empty = len(values) - len(filtered_non_empty)
    if not filtered_non_empty:
        raise ValueError("유효한 값이 없습니다. (태그 없음)")

    filtered_values, summary = filter_value_conflicts(filtered_non_empty)
    if not filtered_values:
        raise ValueError("충돌 제거 후 남는 값이 없습니다.")

    name = (variable_name or auto_name or path.stem).strip()
    variable = Variable(name=name, values=filtered_values)
    stats = {
        "source": "preset_json",
        "total_values": len(values),
        "valid_values": len(filtered_non_empty),
        "imported_values": len(filtered_values),
        "removed_empty": removed_empty,
        "removed_conflicts": len(summary.removed_indices),
        "preset_name": auto_name or "",
        "path": str(path),
    }
    return variable, stats
