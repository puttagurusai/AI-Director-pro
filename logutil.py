"""Write a generate log next to the addon so we can inspect packing/PH."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

LOG = Path(__file__).resolve().parent / "generate.log"


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print("AIDIR", msg)
