from __future__ import annotations

import time


def format_eta(processed: int, total: int, start_time: float) -> str:
    if processed <= 0:
        return "--:--:--"
    elapsed = time.monotonic() - start_time
    remaining = max(0, total - processed)
    eta_seconds = int(remaining * elapsed / processed)
    hours = eta_seconds // 3600
    minutes = (eta_seconds % 3600) // 60
    seconds = eta_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
