from __future__ import annotations

from collections import Counter
import logging
from pathlib import Path
import shutil

from core.preset import Preset
from core.runner import build_variable_specs, match_variable_specs
from core.utils import ensure_unique_name, iter_image_files, render_template

from .common import (
    CancelCallback,
    ProgressCallback,
    build_variable_value_specs,
    explain_unknown_match,
    get_tags_cached,
    sanitize_folder_template_path,
    template_to_variables_payload,
)

_logger = logging.getLogger(__name__)


def move_images(
    preset: Preset,
    folder: str,
    target_root: str,
    order: list[str] | str,
    *,
    folder_template: str = "",
    dry_run: bool = True,
    include_negative: bool = False,
    progress_cb: ProgressCallback | None = None,
    cancel_cb: CancelCallback | None = None,
) -> list[dict]:
    if isinstance(order, str):
        order = [item.strip() for item in order.split(",") if item.strip()]
    if not order:
        raise ValueError("분류 변수 순서를 입력하세요.")

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

    template_text = folder_template.strip() or "/".join(f"[{name}]" for name in order)

    image_paths = iter_image_files(folder)
    total = len(image_paths)
    reserved_map: dict[str, set[str]] = {}
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

        values_map: dict[str, str] = {}
        matched_prefix_order: list[str] = []
        failed_variable: str | None = None
        failed_match: dict = {}
        failed_status: str | None = None
        for variable_name in order:
            match = matches.get(variable_name)
            if not match or match.get("status") != "OK":
                failed_status = (
                    "CONFLICT"
                    if match and match.get("status") == "CONFLICT"
                    else "UNKNOWN"
                )
                failed_variable = variable_name
                failed_match = match or {}
                break
            values_map[variable_name] = str(match.get("values", [""])[0])
            matched_prefix_order.append(variable_name)

        if not matched_prefix_order:
            status = failed_status or "UNKNOWN"
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

        partial_message: str | None = None
        if len(matched_prefix_order) < len(order):
            next_variable = failed_variable or order[len(matched_prefix_order)]
            if failed_status == "CONFLICT":
                conflict_values = list(failed_match.get("values") or [])
                if conflict_values:
                    preview = ", ".join(conflict_values[:4])
                    if len(conflict_values) > 4:
                        preview = f"{preview}, ..."
                    partial_reason = f"{next_variable} 다중 매치({preview})"
                else:
                    partial_reason = f"{next_variable} 다중 매치"
            else:
                reason = explain_unknown_match(
                    next_variable,
                    value_specs_by_variable.get(next_variable, []),
                    tags,
                )
                partial_reason = f"{next_variable} 미매치({reason})"
            partial_message = (
                f"부분 분류: {' > '.join(matched_prefix_order)}까지만 매치, {partial_reason}"
            )

        render_template_text = template_text
        if len(matched_prefix_order) < len(order):
            # 상위부터 연속으로 매치된 prefix 깊이까지만 폴더를 만든다.
            render_template_text = "/".join(f"[{name}]" for name in matched_prefix_order)
        rendered = render_template(
            render_template_text,
            {
                **values_map,
                "value": values_map.get(matched_prefix_order[0], ""),
            },
        )
        folder_name = sanitize_folder_template_path(rendered)
        if not folder_name:
            results.append(
                {
                    "status": "ERROR",
                    "source": path,
                    "target": None,
                    "message": "폴더 이름이 비어 있습니다.",
                    "preview": path,
                }
            )
            if progress_cb:
                progress_cb(idx, total)
            continue

        target_folder = str(Path(target_root) / folder_name)
        if target_folder not in reserved_map:
            try:
                names = {p.name.lower() for p in Path(target_folder).glob("*") if p.is_file()}
            except FileNotFoundError:
                names = set()
            reserved_map[target_folder] = names

        reserved = reserved_map[target_folder]
        ext = Path(path).suffix
        base = Path(path).stem
        new_name = ensure_unique_name(target_folder, base, ext, reserved)
        target = str(Path(target_folder) / new_name)

        if not dry_run:
            Path(target_folder).mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(path, target)
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
                "message": partial_message,
                "preview": preview_source,
            }
        )
        if progress_cb:
            progress_cb(idx, total)

    _logger.info("move cache: hit=%d miss=%d total=%d", cache_hits, cache_misses, total)
    if unknown_reason_counter:
        _logger.info(
            "move unknown detail (top5): %s",
            "; ".join(
                f"{reason} x{count}" for reason, count in unknown_reason_counter.most_common(5)
            ),
        )
    return results
