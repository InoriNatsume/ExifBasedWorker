from __future__ import annotations

import sys
from pathlib import Path

# python tools\filename_tag_tool\filename_value_extractor_gui.py 형태 실행 지원
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from tools.filename_tag_tool.filename_extractor_app.main import main
except ModuleNotFoundError:
    # 파일 직접 실행 시 script 디렉터리 기준 fallback
    from filename_extractor_app.main import main  # type: ignore


if __name__ == "__main__":
    main()
