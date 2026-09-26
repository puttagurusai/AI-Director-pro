"""Headless: blender --background --python tests/addon/apply_offline.py -- park"""

from __future__ import annotations

import sys
from pathlib import Path

ADDON = Path(__file__).resolve().parents[3]
PARENT = ADDON.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import bpy  # noqa: E402

from ai_director_addon.apply import apply_ir  # noqa: E402
from ai_director_addon.fixtures import load_fixture, resolve_domain  # noqa: E402


def main() -> None:
    domain = "park"
    if "--" in sys.argv:
        rest = sys.argv[sys.argv.index("--") + 1 :]
        if rest:
            domain = rest[0]
    domain = resolve_domain(domain, "")
    ir = load_fixture(domain)
    apply_ir(ir)
    n = len([o for o in bpy.data.objects if o.get("aidir.job_id") == ir["job_id"]])
    print("APPLY_OK", domain, "objects", n)
    if n < 3:
        raise SystemExit("too few objects")


if __name__ == "__main__":
    main()
