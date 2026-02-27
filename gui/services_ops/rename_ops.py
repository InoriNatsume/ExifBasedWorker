from __future__ import annotations

from collections import Counter
import logging
import os
from pathlib import Path

from core.preset import Preset
from core.runner import build_variable_specs, match_variable_specs
from core.utils import ensure_unique_name, iter_image_files, render_template, sanitize_filename

from .common import (
    CancelCallback,
    ProgressCallback,
    build_variable_value_specs,
    explain_unknown_match,
    get_tags_cached,
    template_to_variables_payload,
)

_logger = logging.getLogger(__name__)


def rename_images(
    preset: Preset,
    folder: str,
    order: list[str] | str,
    *,
    template: str = "",
    dry_run: bool = True,
    prefix_mode: bool = False,
    include_negative: bool = False,
    progress_cb: ProgressCallback | None = None,
    cancel_cb: CancelCallback | None = None,
) -> list[dict]:
    if isinstance(order, str):
        order = [item.strip() for item in order.split(",") if item.strip()]
    if not order:
        raise ValueError("변수 순서가 비어 있습니다.")

    variables_payload = template_to_variables_payload(preset)
    variable_specs = build_variable_specs(variables_payload)
    spec_names = {item.get("name") for item in variable_specs}
    missing = [name for name in order if name not in spec_names]
    if missing:
        raise ValueError(f"템플릿에 없는 변수: {', '.join(missing)}")
    value_specs_by_variable: dict[str, list[tuple[str, set[str]]]] = {}
    for variable_name in order:
        selected_variable_spec = next(
            (item for item in variable_specs if item.get("name") == variable_name),
            None,
        )
        value_specs_by_variable[variable_name] = build_variable_value_specs(
            selected_variable_spec or {}
        )

    template_text = template.strip() or "_".join(f"[{name}]" for name in order)
    image_paths = iter_image_files(folder)
    total = len(image_paths)
    reserved = {Path(path).name.lower() for path in image_paths}

    results: list[dict] = []
    cache_hits = 0
    cache_misses = 0
    unknown_reason_counter: Counter[str] = Counter()
    for idx, path in enumerate(image_paths, start=1):
        if cancel_cb and cancel_cb():
            break
        try:
            tags, cache_status = get_tags_cached(path, include_negative)
            if cache_status is True:
                cache_hits += 1
            elif cache_status is False:
                cache_misses += 1
            matches = match_variable_specs(variable_specs, tags)
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
            continue

        status = "OK"
        values_map: dict[str, str] = {}
        failed_variable: str | None = None
        failed_match: dict = {}
        for key in order:
            match = matches.get(key)
            if not match or match.get("status") != "OK":
                status = "CONFLICT" if match and match.get("status") == "CONFLICT" else "UNKNOWN"
                failed_variable = key
                failed_match = match or {}
                break
            values_map[key] = match.get("values", [""])[0]

        if status != "OK":
            message: str | None = None
            if status == "UNKNOWN":
                reason_variable = failed_variable or order[0]
                reason = explain_unknown_match(
                    reason_variable,
                    value_specs_by_variable.get(reason_variable, []),
                    tags,
                )
                message = f"{reason_variable}: {reason}"
                unknown_reason_counter[message] += 1
            elif status == "CONFLICT":
                conflict_values = list(failed_match.get("values") or [])
                if conflict_values:
                    preview = ", ".join(conflict_values[:4])
                    if len(conflict_values) > 4:
                        preview = f"{preview}, ..."
                    prefix = f"{failed_variable}: " if failed_variable else ""
                    message = f"{prefix}다중 매치: {preview}"
                else:
                    prefix = f"{failed_variable}: " if failed_variable else ""
                    message = f"{prefix}다중 매치 발생"
            results.append(
                {
                    "status": status,
                    "source": path,
                    "target": None,
                    "message": message,
                    "preview": path,
                }
            )
            if progress_cb:
                progress_cb(idx, total)
            continue

        base_name = sanitize_filename(render_template(template_text, values_map))
        if prefix_mode:
            stem = Path(path).stem
            if base_name:
                joiner = "" if base_name.endswith("_") else "_"
                base_name = f"{base_name}{joiner}{stem}"
            else:
                base_name = stem

        ext = Path(path).suffix
        current_name = Path(path).name
        candidate = f"{base_name}{ext}"
        if candidate.lower() == current_name.lower():
            new_name = current_name
        else:
            new_name = ensure_unique_name(Path(path).parent, base_name, ext, reserved)
        target = str(Path(path).with_name(new_name))

        if not dry_run and target != path:
            try:
                os.rename(path, target)
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
                continue

        preview_source = path if dry_run else target
        results.append(
            {
                "status": "OK",
                "source": path,
                "target": target,
                "message": None,
                "preview": preview_source,
            }
        )
        if progress_cb:
            progress_cb(idx, total)

    _logger.info("rename cache: hit=%d miss=%d total=%d", cache_hits, cache_misses, total)
    if unknown_reason_counter:
        _logger.info(
            "rename unknown detail (top5): %s",
            "; ".join(
                f"{reason} x{count}" for reason, count in unknown_reason_counter.most_common(5)
            ),
        )
    return results
