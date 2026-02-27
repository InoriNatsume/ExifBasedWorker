from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".avif",
}

STATUS_MATCH = "MATCH"
STATUS_NAME_MISMATCH = "NAME_MISMATCH"
STATUS_FINGERPRINT_NOT_FOUND = "FINGERPRINT_NOT_FOUND"
STATUS_SOURCE_DUPLICATE = "SOURCE_DUPLICATE"
STATUS_READ_ERROR = "READ_ERROR"

ALL_STATUSES = [
    STATUS_MATCH,
    STATUS_NAME_MISMATCH,
    STATUS_FINGERPRINT_NOT_FOUND,
    STATUS_SOURCE_DUPLICATE,
    STATUS_READ_ERROR,
]


@dataclass
class FileEntry:
    path: str
    filename: str
    norm_name: str
    fingerprint: str | None
    error: str | None = None


@dataclass
class CompareRecord:
    status: str
    result_path: str
    result_name: str
    result_fingerprint: str | None
    source_candidates: list[str]
    details: str


def normalize_name(name: str) -> str:
    stem = Path(name).stem.lower()
    cleaned = []
    for ch in stem:
        if ch.isalnum():
            cleaned.append(ch)
    return "".join(cleaned)


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def iter_image_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for root, _, names in os.walk(folder):
        root_path = Path(root)
        for name in names:
            p = root_path / name
            if is_image_file(p):
                files.append(p)
    files.sort()
    return files


def hash_file(path: str) -> str:
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def dhash_file(path: str, size: int = 8) -> str:
    with Image.open(path) as img:
        gray = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    bits = 0
    idx = 0
    for row in range(size):
        base = row * (size + 1)
        for col in range(size):
            left = pixels[base + col]
            right = pixels[base + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
            idx += 1
    hex_len = (idx + 3) // 4
    return f"{bits:0{hex_len}x}"


def fingerprint_file_task(args: tuple[str, str]) -> tuple[str, str | None, str | None]:
    path, mode = args
    try:
        if mode == "dhash":
            fp = dhash_file(path)
        else:
            fp = hash_file(path)
        return path, fp, None
    except Exception as exc:
        return path, None, str(exc)


def compute_entries(
    paths: list[Path],
    mode: str,
    workers: int,
    stop_event: threading.Event | None = None,
    progress: Callable[[str, int, int], None] | None = None,
    bind_executor: Callable[[ProcessPoolExecutor | None], None] | None = None,
) -> tuple[list[FileEntry], bool]:
    entries: list[FileEntry] = []
    total = len(paths)
    if total == 0:
        return entries, False

    by_path: dict[str, FileEntry] = {}
    for p in paths:
        key = str(p)
        by_path[key] = FileEntry(
            path=key,
            filename=p.name,
            norm_name=normalize_name(p.name),
            fingerprint=None,
            error=None,
        )

    workers = max(1, min(workers, os.cpu_count() or 1))
    tasks = [(str(p), mode) for p in paths]
    cancelled = False
    done = 0

    ex: ProcessPoolExecutor | None = None
    try:
        ex = ProcessPoolExecutor(max_workers=workers)
        if bind_executor:
            bind_executor(ex)
        pending = {ex.submit(fingerprint_file_task, task): task[0] for task in tasks}

        while pending:
            if stop_event is not None and stop_event.is_set():
                cancelled = True
                for fut in pending:
                    fut.cancel()
                ex.shutdown(wait=False, cancel_futures=True)
                break

            done_set, _ = wait(
                pending.keys(),
                timeout=0.2,
                return_when=FIRST_COMPLETED,
            )
            if not done_set:
                continue

            for future in done_set:
                p = pending.pop(future)
                entry = by_path[p]
                try:
                    _, fp, err = future.result()
                    entry.fingerprint = fp
                    entry.error = err
                except Exception as exc:
                    entry.fingerprint = None
                    entry.error = str(exc)
                done += 1
                if progress:
                    progress("fingerprint", done, total)
    finally:
        if bind_executor:
            bind_executor(None)
        if ex is not None:
            if not cancelled:
                ex.shutdown(wait=True, cancel_futures=False)
            else:
                _terminate_executor_processes(ex)

    for p in paths:
        entries.append(by_path[str(p)])
    return entries, cancelled


def _terminate_executor_processes(ex: ProcessPoolExecutor) -> None:
    # 표준 API에는 즉시 kill이 없어 내부 프로세스를 best-effort로 정리한다.
    processes = getattr(ex, "_processes", None)
    if not processes:
        return
    try:
        values = list(processes.values())
    except Exception:
        return
    for proc in values:
        try:
            if proc is not None and proc.is_alive():
                proc.terminate()
        except Exception:
            pass


def compare_entries(
    source_entries: list[FileEntry],
    result_entries: list[FileEntry],
) -> tuple[list[CompareRecord], dict[str, list[FileEntry]]]:
    source_index: dict[str, list[FileEntry]] = {}
    for src in source_entries:
        if src.fingerprint is None:
            continue
        source_index.setdefault(src.fingerprint, []).append(src)

    records: list[CompareRecord] = []
    for res in result_entries:
        if res.error:
            records.append(
                CompareRecord(
                    status=STATUS_READ_ERROR,
                    result_path=res.path,
                    result_name=res.filename,
                    result_fingerprint=res.fingerprint,
                    source_candidates=[],
                    details=f"결과 파일 읽기 실패: {res.error}",
                )
            )
            continue

        if not res.fingerprint:
            records.append(
                CompareRecord(
                    status=STATUS_READ_ERROR,
                    result_path=res.path,
                    result_name=res.filename,
                    result_fingerprint=None,
                    source_candidates=[],
                    details="결과 파일 지문 생성 실패",
                )
            )
            continue

        candidates = source_index.get(res.fingerprint, [])
        if not candidates:
            records.append(
                CompareRecord(
                    status=STATUS_FINGERPRINT_NOT_FOUND,
                    result_path=res.path,
                    result_name=res.filename,
                    result_fingerprint=res.fingerprint,
                    source_candidates=[],
                    details="원본 폴더에서 같은 지문을 찾지 못함",
                )
            )
            continue

        if len(candidates) > 1:
            names = ", ".join(c.filename for c in candidates[:3])
            more = f" 외 {len(candidates) - 3}개" if len(candidates) > 3 else ""
            records.append(
                CompareRecord(
                    status=STATUS_SOURCE_DUPLICATE,
                    result_path=res.path,
                    result_name=res.filename,
                    result_fingerprint=res.fingerprint,
                    source_candidates=[c.path for c in candidates],
                    details=f"원본에 동일 지문이 {len(candidates)}개: {names}{more}",
                )
            )
            continue

        src = candidates[0]
        if src.filename.lower() == res.filename.lower():
            status = STATUS_MATCH
            detail = "이름 일치"
        elif src.norm_name == res.norm_name:
            status = STATUS_MATCH
            detail = "정규화 이름 일치(구분자/공백 무시)"
        else:
            status = STATUS_NAME_MISMATCH
            detail = f"원본 이름: {src.filename}"

        records.append(
            CompareRecord(
                status=status,
                result_path=res.path,
                result_name=res.filename,
                result_fingerprint=res.fingerprint,
                source_candidates=[src.path],
                details=detail,
            )
        )

    return records, source_index


class CompareWorker(threading.Thread):
    def __init__(
        self,
        source_dir: str,
        result_dir: str,
        mode: str,
        workers: int,
        out_queue: "queue.Queue[dict[str, Any]]",
        stop_event: threading.Event,
    ) -> None:
        super().__init__(daemon=True)
        self.source_dir = source_dir
        self.result_dir = result_dir
        self.mode = mode
        self.workers = workers
        self.out_queue = out_queue
        self.stop_event = stop_event
        self._executor_lock = threading.Lock()
        self._executor: ProcessPoolExecutor | None = None

    def _bind_executor(self, ex: ProcessPoolExecutor | None) -> None:
        with self._executor_lock:
            self._executor = ex

    def request_stop(self) -> None:
        self.stop_event.set()
        with self._executor_lock:
            ex = self._executor
        if ex is not None:
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            _terminate_executor_processes(ex)

    def _put(self, payload: dict[str, Any]) -> None:
        self.out_queue.put(payload)

    def run(self) -> None:
        started = time.perf_counter()
        try:
            src_dir = Path(self.source_dir)
            res_dir = Path(self.result_dir)
            if not src_dir.is_dir():
                raise ValueError(f"원본 폴더가 유효하지 않습니다: {src_dir}")
            if not res_dir.is_dir():
                raise ValueError(f"결과 폴더가 유효하지 않습니다: {res_dir}")

            self._put({"type": "stage", "text": "원본/결과 파일 스캔 중..."})
            source_paths = iter_image_files(src_dir)
            result_paths = iter_image_files(res_dir)
            self._put(
                {
                    "type": "scan_done",
                    "source_total": len(source_paths),
                    "result_total": len(result_paths),
                }
            )

            if self.stop_event.is_set():
                self._put({"type": "cancelled"})
                return

            def src_progress(_kind: str, done: int, total: int) -> None:
                self._put({"type": "progress", "stage": "원본 지문", "done": done, "total": total})

            def res_progress(_kind: str, done: int, total: int) -> None:
                self._put({"type": "progress", "stage": "결과 지문", "done": done, "total": total})

            source_entries, cancelled = compute_entries(
                source_paths,
                mode=self.mode,
                workers=self.workers,
                stop_event=self.stop_event,
                progress=src_progress,
                bind_executor=self._bind_executor,
            )
            if cancelled or self.stop_event.is_set():
                self._put({"type": "cancelled"})
                return

            result_entries, cancelled = compute_entries(
                result_paths,
                mode=self.mode,
                workers=self.workers,
                stop_event=self.stop_event,
                progress=res_progress,
                bind_executor=self._bind_executor,
            )
            if cancelled or self.stop_event.is_set():
                self._put({"type": "cancelled"})
                return

            self._put({"type": "stage", "text": "비교 중..."})
            records, source_index = compare_entries(source_entries, result_entries)

            source_dupes = {fp: items for fp, items in source_index.items() if len(items) > 1}
            counts = {status: 0 for status in ALL_STATUSES}
            for rec in records:
                counts[rec.status] = counts.get(rec.status, 0) + 1

            elapsed = time.perf_counter() - started
            self._put(
                {
                    "type": "done",
                    "records": records,
                    "source_entries": source_entries,
                    "result_entries": result_entries,
                    "source_duplicates": source_dupes,
                    "counts": counts,
                    "elapsed": elapsed,
                    "mode": self.mode,
                }
            )
        except Exception as exc:
            self._put({"type": "error", "message": str(exc)})
