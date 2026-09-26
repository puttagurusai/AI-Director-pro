"""Load bundled SceneIR fixtures by domain."""

from __future__ import annotations

import json
from pathlib import Path

from .ir import validate_scene_ir

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures"

DOMAIN_FILES = {
    "interior": "living_room_v0.json",
    "park": "park_v0.json",
    "forest": "forest_v0.json",
    "city": "city_v0.json",
    "zoo": "zoo_v0.json",
    "space": "space_v0.json",
    "beach": "beach_v0.json",
    "generic": "generic_v0.json",
}

KEYWORDS = (
    ("space", ("space", "orbit", "station", "planet", "nasa", "zero-g", "spaceship")),
    ("zoo", ("zoo", "safari", "enclosure", "habitat", "lion", "tiger")),
    ("forest", ("forest", "woods", "jungle", "clearing")),
    ("park", ("park", "playground", "garden", "pond", "bench")),
    ("city", ("city", "street", "downtown", "alley", "skyscraper")),
    ("beach", ("beach", "shore", "ocean", "sand", "umbrella")),
    ("interior", ("living room", "bedroom", "office", "kitchen", "interior", "apartment", "sofa")),
)


def infer_domain(prompt: str) -> str:
    text = (prompt or "").lower()
    for domain, keys in KEYWORDS:
        if any(k in text for k in keys):
            return domain
    return "generic"


def resolve_domain(ui_domain: str, prompt: str) -> str:
    if ui_domain and ui_domain != "auto":
        return ui_domain
    return infer_domain(prompt)


def load_fixture(domain: str) -> dict:
    name = DOMAIN_FILES.get(domain) or DOMAIN_FILES["generic"]
    path = FIXTURE_DIR / name
    if not path.is_file():
        path = FIXTURE_DIR / DOMAIN_FILES["generic"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate_scene_ir(doc)
    return doc
