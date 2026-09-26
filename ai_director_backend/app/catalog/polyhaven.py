"""Poly Haven CC0 lookup. Unique User-Agent required."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = "AIDirector/0.1 (+local ingest; https://polyhaven.com/our-api)"
BASE = "https://api.polyhaven.com"
DATA = Path(os.environ.get("AIDIR_DATA", Path(__file__).resolve().parents[2] / "data"))

CATEGORY_QUERY = {
    "sofa": ("models", "furniture", "sofa"),
    "armchair": ("models", "furniture", "chair"),
    "dining_chair": ("models", "furniture", "chair"),
    "stool": ("models", "furniture", "stool"),
    "ottoman": ("models", "furniture", "ottoman"),
    "coffee_table": ("models", "furniture", "table"),
    "dining_table": ("models", "furniture", "table"),
    "desk": ("models", "furniture", "desk"),
    "nightstand": ("models", "furniture", "nightstand"),
    "side_table": ("models", "furniture", "table"),
    "bed": ("models", "furniture", "bed"),
    "bookshelf": ("models", "furniture", "shelf"),
    "cabinet": ("models", "furniture", "cabinet"),
    "dresser": ("models", "furniture", "cabinet"),
    "lamp_floor": ("models", "furniture", "lamp"),
    "plant": ("models", "plants", "plant"),
    "tree": ("models", "plants", "tree"),
    "bush": ("models", "plants", "bush"),
    "bench": ("models", "furniture", "bench"),
    "rock": ("models", "nature", "rock"),
    "mirror": ("models", "furniture", "mirror"),
}

HDRI_PRESET = {
    "warm_interior": "interior",
    "high_key": "studio",
    "soft_day": "clear",
    "overcast": "overcast",
    "sunset": "sunset",
    "night_urban": "night",
    "stars": "night",
    "noir": "night",
}

SKIP_CATEGORIES = {
    "animal",
    "vehicle",
    "building_mass",
    "path",
    "sidewalk",
    "enclosure",
    "habitat",
    "planet",
    "module",
    "rug",
    "art_frame",
    "sign",
    "pond",
    "umbrella",
    "towel",
}


def _get(url: str, timeout: float = 20.0) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _cache_path(name: str) -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    return DATA / name


def list_assets(kind: str, category: str | None = None) -> dict:
    q = {"t": kind}
    if category:
        q["c"] = category
    cache = _cache_path(f"ph_{kind}_{category or 'all'}.json")
    if cache.is_file() and cache.stat().st_size > 10:
        return json.loads(cache.read_text(encoding="utf-8"))
    url = BASE + "/assets?" + urllib.parse.urlencode(q)
    data = _get(url)
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data if isinstance(data, dict) else {}


def files_for(asset_id: str) -> dict:
    return _get(f"{BASE}/files/{urllib.parse.quote(asset_id)}")


def _glb_url(files: dict) -> tuple[str | None, str | None]:
    gltf = files.get("glTF") or files.get("gltf") or {}
    if not isinstance(gltf, dict):
        return None, None
    # resolutions like 1k, 2k, 4k
    for res in ("1k", "2k", "4k", "8k"):
        block = gltf.get(res)
        if not isinstance(block, dict):
            continue
        glb = block.get("glb") or block.get("gltf")
        if isinstance(glb, dict) and glb.get("url"):
            return str(glb["url"]), res
        if isinstance(glb, str) and glb.startswith("http"):
            return glb, res
    for block in gltf.values():
        if isinstance(block, dict):
            glb = block.get("glb")
            if isinstance(glb, dict) and glb.get("url"):
                return str(glb["url"]), "unk"
    return None, None


def _hdri_url(files: dict) -> str | None:
    hdr = files.get("hdri") or {}
    for res in ("2k", "1k", "4k"):
        block = hdr.get(res) if isinstance(hdr, dict) else None
        if isinstance(block, dict):
            exr = block.get("hdr") or block.get("exr")
            if isinstance(exr, dict) and exr.get("url"):
                return str(exr["url"])
    return None


def search_model(category: str, extra: str = "") -> dict | None:
    if category in SKIP_CATEGORIES:
        return None
    kind, ph_cat, needle = CATEGORY_QUERY.get(category, ("models", None, category.replace("_", " ")))
    try:
        assets = list_assets(kind, ph_cat)
    except Exception:
        return None
    needle = (needle + " " + extra).lower().strip()
    tokens = [t for t in re.split(r"\W+", needle) if t]
    best_id = None
    best_score = 0
    for aid, meta in assets.items():
        if not isinstance(meta, dict):
            continue
        blob = " ".join(
            [
                aid,
                str(meta.get("name") or ""),
                " ".join(str(t) for t in (meta.get("tags") or [])),
            ]
        ).lower()
        score = sum(1 for t in tokens if t in blob)
        if score > best_score:
            best_score = score
            best_id = aid
    if not best_id or best_score <= 0:
        return None
    try:
        files = files_for(best_id)
    except Exception:
        return None
    url, res = _glb_url(files)
    if not url:
        return None
    dims = None
    meta = assets.get(best_id) or {}
    if isinstance(meta, dict):
        dims = meta.get("dimensions")
    size_m = None
    if isinstance(dims, (list, tuple)) and len(dims) >= 3:
        size_m = (float(dims[0]) / 1000.0, float(dims[1]) / 1000.0, float(dims[2]) / 1000.0)
    return {
        "catalog_id": f"ph_{best_id}",
        "ph_id": best_id,
        "url": url,
        "resolution": res,
        "real_size_m": size_m,
        "attribution": f"{best_id} — CC0, Poly Haven",
    }


def pick_hdri(preset: str, domain: str) -> dict | None:
    tag = HDRI_PRESET.get(preset, "outdoor")
    if domain == "interior" and preset in ("warm_interior", "high_key"):
        tag = "indoor"
    if domain == "space":
        tag = "night"
    try:
        assets = list_assets("hdris")
    except Exception:
        return None
    best_id = None
    best = 0
    for aid, meta in assets.items():
        blob = (aid + " " + " ".join(str(t) for t in (meta or {}).get("tags") or [])).lower()
        score = blob.count(tag) + (2 if tag in aid.lower() else 0)
        if domain == "park" and "park" in blob:
            score += 2
        if domain == "forest" and "forest" in blob:
            score += 2
        if score > best:
            best, best_id = score, aid
    if not best_id:
        best_id = next(iter(assets), None)
    if not best_id:
        return None
    try:
        files = files_for(best_id)
    except Exception:
        return None
    url = _hdri_url(files)
    if not url:
        return None
    return {
        "catalog_id": f"ph_hdri_{best_id}",
        "ph_id": best_id,
        "url": url,
        "attribution": f"{best_id} HDRI — CC0, Poly Haven",
    }


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 64:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())
    return dest
