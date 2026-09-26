"""Full Poly Haven model index. Sample from all 500+ meshes, not /search top-20."""

from __future__ import annotations

import json
import random
from pathlib import Path

from . import polyhaven as ph
from .logutil import log

# Our scene category → match on PH categories[] / tags[] / slug (lowercase).
FILTERS = {
    "tree": {"cats": ("trees",), "tags": ("tree", "pine", "oak", "fir", "palm")},
    "bush": {"cats": ("plants", "ground cover"), "tags": ("shrub", "bush", "grass")},
    "plant": {"cats": ("plants",), "tags": ("plant", "pot", "fern", "flower")},
    "rock": {"cats": ("rocks",), "tags": ("rock", "boulder")},
    "bench": {"cats": ("seating",), "tags": ("bench",)},
    "sofa": {"cats": ("furniture", "seating"), "tags": ("sofa", "couch")},
    "dining_chair": {"cats": ("seating", "furniture"), "tags": ("chair",)},
    "coffee_table": {"cats": ("table", "furniture"), "tags": ("table", "coffee")},
    "desk": {"cats": ("furniture", "table"), "tags": ("desk",)},
    "bookshelf": {"cats": ("shelves", "furniture"), "tags": ("shelf", "book")},
    "side_table": {"cats": ("table", "furniture"), "tags": ("table",)},
    "lamp_floor": {"cats": ("lighting",), "tags": ("lamp",)},
    "streetlamp": {"cats": ("lighting",), "tags": ("lamp", "lantern", "light")},
    "crate": {"cats": ("containers",), "tags": ("crate", "box", "barrel")},
    "umbrella": {"cats": ("props",), "tags": ("umbrella",)},
    "bed": {"cats": ("furniture",), "tags": ("bed",)},
    "animal": {"cats": ("props",), "tags": ("horse", "statue", "animal")},
    "pond": {"cats": ("props", "nature"), "tags": ("fountain", "water", "pond", "pool")},
}

_library: dict | None = None

TEX_FILTERS = {
    "grass": {"cats": ("terrain", "natural", "outdoor"), "tags": ("grass", "lawn", "ground")},
    "dirt": {"cats": ("terrain", "natural"), "tags": ("dirt", "soil", "ground", "mud")},
    "sand": {"cats": ("sand", "terrain"), "tags": ("sand", "beach")},
    "pavement": {"cats": ("concrete", "man made"), "tags": ("asphalt", "concrete", "pavement", "road")},
    "floor": {"cats": ("floor", "wood", "indoor"), "tags": ("wood", "floor", "plank")},
    "wall": {"cats": ("wall", "plaster-concrete", "brick"), "tags": ("plaster", "brick", "wall")},
    "trail": {"cats": ("terrain", "natural"), "tags": ("dirt", "path", "gravel", "ground")},
    "path": {"cats": ("concrete", "man made"), "tags": ("asphalt", "road", "paving")},
}

HDRI_FILTERS = {
    "sunset": {"cats": ("sunrise-sunset", "outdoor"), "tags": ("sunset", "dusk", "sunrise")},
    "soft_day": {"cats": ("outdoor", "nature", "clear"), "tags": ("day", "clear", "sunny")},
    "overcast": {"cats": ("nature", "outdoor"), "tags": ("overcast", "cloud", "forest")},
    "warm_interior": {"cats": ("indoor",), "tags": ("indoor", "studio", "interior")},
    "night_urban": {"cats": ("urban",), "tags": ("night", "city", "street")},
    "stars": {"cats": ("skies",), "tags": ("night", "star", "sky")},
    "high_key": {"cats": ("indoor",), "tags": ("studio",)},
    "noir": {"cats": ("urban",), "tags": ("night",)},
}


def _cache_path(name: str = "ph_library.json") -> Path:
    try:
        import bpy

        root = Path(bpy.utils.user_resource("DATAFILES", path="ai_director", create=True))
    except Exception:
        root = Path(__file__).resolve().parent / "data"
        root.mkdir(parents=True, exist_ok=True)
    return root / name


def load_library(force: bool = False) -> dict:
    """Store models + textures + HDRIs + collection kits from Poly Haven."""
    global _library
    if _library is not None and not force:
        return _library
    path = _cache_path()
    if path.is_file() and not force:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("models"):
                _library = data
                log(
                    f"ph library cache models={len(data.get('models') or {})} "
                    f"tex={len(data.get('textures') or {})} hdri={len(data.get('hdris') or {})} "
                    f"kits={len(data.get('collections') or {})}"
                )
                return _library
        except Exception:
            pass
    models = ph._get("/assets?t=models") or {}
    textures = ph._get("/assets?t=textures") or {}
    hdris = ph._get("/assets?t=hdris") or {}
    if not isinstance(models, dict):
        models = {}
    if not isinstance(textures, dict):
        textures = {}
    if not isinstance(hdris, dict):
        hdris = {}
    collections: dict[str, list[str]] = {}
    for slug, meta in models.items():
        if not isinstance(meta, dict):
            continue
        for c in meta.get("categories") or []:
            cl = str(c).lower()
            if cl.startswith("collection:"):
                name = cl.split(":", 1)[-1].strip()
                collections.setdefault(name, []).append(slug)
    _library = {"models": models, "textures": textures, "hdris": hdris, "collections": collections}
    try:
        path.write_text(json.dumps(_library), encoding="utf-8")
    except Exception:
        pass
    log(
        f"ph library fetched models={len(models)} tex={len(textures)} "
        f"hdri={len(hdris)} kits={list(collections)[:8]}"
    )
    return _library


def load_index(force: bool = False) -> dict:
    return load_library(force).get("models") or {}


def _blob(slug: str, meta: dict) -> str:
    cats = " ".join(str(c) for c in (meta.get("categories") or []))
    tags = " ".join(str(t) for t in (meta.get("tags") or []))
    return f"{slug} {meta.get('name') or ''} {cats} {tags} {meta.get('category') or ''}".lower()


BAN = (
    "bust", "statue", "sculpture", "marble", "column", "vase", "urn",
    "cliff", "ship", "boat", "cannon", "sword", "hose", "ladder",
    "container", "bucket", "watering", "plastic",
)
MUST_SLUG = {
    "rock": ("rock", "boulder"),
    "tree": ("tree", "pine", "oak", "fir", "palm", "sapling", "quiver"),
    "bench": ("bench",),
    "sofa": ("sofa", "couch"),
    "bush": ("shrub", "bush"),
    "streetlamp": ("lamp", "lantern", "streetlight"),
}


def candidates(category: str) -> list[str]:
    """All PH slugs that belong to this scene category."""
    idx = load_index()
    spec = FILTERS.get(category)
    if not spec:
        return []
    want_c = spec["cats"]
    want_t = spec["tags"]
    must = MUST_SLUG.get(category)
    hits = []
    for slug, meta in idx.items():
        if not isinstance(meta, dict):
            continue
        low = slug.lower()
        if any(b in low for b in BAN):
            continue
        cats = [str(c).lower() for c in (meta.get("categories") or [])]
        blob = _blob(slug, meta)
        if must and not any((" " + m + " ") in (" " + blob.replace("_", " ") + " ") or m in low for m in must):
            continue
        cat_hit = any(c in cats for c in want_c)
        tag_hit = any((" " + t + " ") in (" " + blob.replace("_", " ") + " ") for t in want_t)
        if cat_hit or tag_hit:
            hits.append(slug)
    return hits


def sample_slugs(category: str, n: int, rng: random.Random) -> list[str]:
    """Unique PH meshes first; extra copies if we need more instances than unique assets."""
    pool = list(candidates(category))
    if not pool:
        return []
    rng.shuffle(pool)
    if n <= len(pool):
        return pool[:n]
    out = list(pool)
    while len(out) < n:
        out.append(pool[len(out) % len(pool)])
    return out


def hits_for_slugs(slugs: list[str]) -> list[dict]:
    """Resolve downloadable glTF packs (skip huge files)."""
    out = []
    seen = {}
    for slug in slugs:
        if slug in seen:
            if seen[slug]:
                out.append(seen[slug])
            continue
        try:
            pack = ph.gltf_pack(ph.files(slug))
        except Exception:
            pack = None
        if not pack:
            seen[slug] = None
            continue
        hit = {
            "catalog_id": "ph_" + slug,
            "ph_id": slug,
            "url": pack[0][1],
            "text": f"{slug} — CC0, Poly Haven",
            "real_size_m": ph.size_m(slug),
        }
        seen[slug] = hit
        out.append(hit)
    return out


def _filter_slugs(kind: str, key: str, rng: random.Random) -> list[str]:
    lib = load_library()
    if kind == "textures":
        idx, spec = lib.get("textures") or {}, TEX_FILTERS.get(key)
    else:
        idx, spec = lib.get("hdris") or {}, HDRI_FILTERS.get(key)
    if not spec or not idx:
        return []
    hits = []
    for slug, meta in idx.items():
        if not isinstance(meta, dict):
            continue
        blob = _blob(slug, meta)
        cats = [str(c).lower() for c in (meta.get("categories") or [])]
        if any(c in cats or c in blob for c in spec["cats"]) or any(t in blob for t in spec["tags"]):
            hits.append(slug)
    rng.shuffle(hits)
    return hits


def sample_texture(kind: str, rng: random.Random) -> dict | None:
    slugs = _filter_slugs("textures", kind, rng)
    for slug in slugs[:8]:
        try:
            files_tree = ph.files(slug)
            diff = ph._map_url(files_tree, "Diffuse")
        except Exception:
            continue
        if not diff:
            continue
        return {
            "catalog_id": "ph_tex_" + slug,
            "ph_id": slug,
            "diff_url": diff,
            "nor_url": ph._map_url(files_tree, "nor_gl"),
            "rough_url": ph._map_url(files_tree, "Rough"),
            "text": f"{slug} texture — CC0, Poly Haven",
        }
    return ph.pick_texture(kind)


def sample_hdri(preset: str, rng: random.Random) -> dict | None:
    slugs = _filter_slugs("hdris", preset, rng)
    for slug in slugs[:8]:
        try:
            url = ph.hdri_url(ph.files(slug))
        except Exception:
            continue
        if not url:
            continue
        return {
            "catalog_id": "ph_hdri_" + slug,
            "ph_id": slug,
            "url": url,
            "text": f"{slug} HDRI — CC0, Poly Haven",
        }
    return ph.pick_hdri(preset)


def collection_slugs(name: str) -> list[str]:
    return list((load_library().get("collections") or {}).get(name) or [])

