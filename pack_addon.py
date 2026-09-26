"""Build ai_director.zip for Blender Install from Disk."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ai_director.zip"

INCLUDE_FILES = [
    "__init__.py",
    "blender_manifest.toml",
    "apply.py",
    "catalog_cache.py",
    "catalog_index.py",
    "completeness.py",
    "config.json",
    "fixtures.py",
    "gn_scatter.py",
    "groq_client.py",
    "ir.py",
    "ir_schema.json",
    "job_modal.py",
    "layout.py",
    "logutil.py",
    "lookdev.py",
    "mesh_util.py",
    "planner.py",
    "polyhaven.py",
    "prefs.py",
    "secrets.py",
    "status.py",
    "terrain.py",
]
INCLUDE_DIRS = ["kits", "fixtures", "ui"]


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE_FILES:
            path = ROOT / name
            zf.write(path, name)
        for folder in INCLUDE_DIRS:
            for path in (ROOT / folder).rglob("*"):
                if path.is_dir() or path.name == "__pycache__" or path.suffix == ".pyc":
                    continue
                if "__pycache__" in path.parts:
                    continue
                zf.write(path, path.relative_to(ROOT).as_posix())
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
