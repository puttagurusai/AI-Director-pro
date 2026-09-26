"""Official Poly Haven public API client.

Docs: https://polyhaven.com/our-api
Live: https://api.polyhaven.com
No API key. Unique User-Agent required. Credit: Powered by Poly Haven.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://api.polyhaven.com"
UA = "AIDirector/0.2 (Blender addon; https://polyhaven.com/our-api)"
MAX_INCLUDE = 22_000_000

# Category → /search?q=  (t=models)
SEARCH_Q = {
    "tree": "tree",
    "bush": "shrub",
    "plant": "potted plant",
    "rock": "rock boulder",
    "bench": "painted wooden bench",
    "sofa": "sofa",
    "coffee_table": "coffee table",
    "dining_chair": "chair",
    "desk": "desk",
    "bookshelf": "bookshelf",
    "side_table": "side table",
    "lamp_floor": "floor lamp",
    "streetlamp": "lamp post",
    "crate": "crate",
    "umbrella": "umbrella",
    "animal": "horse statue",
    "bed": "bed",
}

HDRI_Q = {
    "sunset": "park sunset",
    "soft_day": "clear sky outdoor",
    "overcast": "forest overcast",
    "warm_interior": "indoor studio",
    "night_urban": "city night",
    "stars": "night sky",
    "high_key": "studio",
    "noir": "night",
}

_cache: dict[str, object] = {}


def _get(path: str, timeout: float = 30) -> dict | list:
    url = API + path
    if url in _cache:
        return _cache[url]  # type: ignore[return-value]
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    _cache[url] = data
    return data


def search(q: str, t: str, limit: int = 12) -> list[dict]:
    qn = (q or "").strip().lower()[:100]
    path = "/search?" + urllib.parse.urlencode({"q": qn, "t": t, "limit": str(limit)})
    body = _get(path)
    if not isinstance(body, dict):
        return []
    return list(body.get("results") or [])


def files(asset_id: str) -> dict:
    data = _get("/files/" + urllib.parse.quote(asset_id))
    return data if isinstance(data, dict) else {}


def info(asset_id: str) -> dict:
    data = _get("/info/" + urllib.parse.quote(asset_id))
    return data if isinstance(data, dict) else {}


def gltf_pack(files_tree: dict) -> list[tuple[str, str]] | None:
    """1k (then 2k) gltf + include textures. Skip packages with a >22MB include."""
    gltf = files_tree.get("gltf") or files_tree.get("glTF") or {}
    if not isinstance(gltf, dict):
        return None
    for res in ("1k", "2k"):
        block = gltf.get(res)
        if not isinstance(block, dict):
            continue
        entry = block.get("gltf") or block.get("glb")
        if not isinstance(entry, dict) or not entry.get("url"):
            continue
        includes = entry.get("include") or {}
        parts = [("__main__", str(entry["url"]))]
        too_big = False
        for rel, meta in includes.items():
            if ((meta or {}).get("size") or 0) > MAX_INCLUDE:
                too_big = True
                break
            url = (meta or {}).get("url")
            if url:
                parts.append((str(rel).replace("\\", "/"), str(url)))
        if too_big:
            continue
        return parts
    return None


def hdri_url(files_tree: dict) -> str | None:
    hdri = files_tree.get("hdri") or {}
    if not isinstance(hdri, dict):
        return None
    for res in ("1k", "2k"):
        block = hdri.get(res)
        if not isinstance(block, dict):
            continue
        item = block.get("hdr") or block.get("exr")
        if isinstance(item, dict) and item.get("url"):
            return str(item["url"])
    return None


def size_m(asset_id: str) -> tuple[float, float, float] | None:
    meta = info(asset_id)
    dims = meta.get("dimensions")
    if isinstance(dims, (list, tuple)) and len(dims) >= 3:
        return (float(dims[0]) / 1000.0, float(dims[1]) / 1000.0, float(dims[2]) / 1000.0)
    return None


_SKIP_ALWAYS = (
    "stump", "dead_tree", "dead_quiver", "vice",
    "roots", "root_cluster", "debris", "rock_0", "dandelion",
    "day_bed", "ceiling", "ladder", "bust", "statue", "sculpture", "marble", "cliff",
    "hose", "container", "plastic", "bucket", "watering",
)
_SKIP_FOR = {
    "bench": ("sofa", "table", "chair", "nightstand", "cabinet", "shelf", "stool", "bookshelf"),
    "tree": ("stump", "dead", "roots", "flower"),
    "streetlamp": ("ceiling", "desk", "floor", "ladder", "container", "plastic"),
    "bush": ("hose", "planter", "watering", "garden_hose"),
}


# Holodeck-lite: category must appear in the PH slug/name (no CLIP).
_MUST = {
    "tree": ("tree", "pine", "oak", "fir", "palm", "birch", "quiver", "sapling"),
    "bench": ("bench",),
    "rock": ("rock", "boulder"),
    "bush": ("shrub", "bush"),
    "sofa": ("sofa", "couch"),
    "plant": ("plant", "fern", "pot", "flower"),
    "streetlamp": ("lamp", "lantern", "streetlight"),
}


def _blob(row: dict) -> str:
    tags = row.get("tags") or []
    if isinstance(tags, list):
        tag_s = " ".join(str(t) for t in tags)
    else:
        tag_s = str(tags)
    return " ".join(
        [
            str(row.get("slug") or ""),
            str(row.get("name") or ""),
            tag_s,
        ]
    ).lower()


def _score(query: str, category: str, row: dict) -> float:
    blob = _blob(row)
    slug = str(row.get("slug") or "").lower()
    if any(bad in slug for bad in _SKIP_ALWAYS):
        return -1.0
    if any(bad in slug for bad in _SKIP_FOR.get(category) or ()):
        return -1.0
    must = _MUST.get(category) or ()
    if must and not any(m in blob for m in must):
        return -1.0
    tokens = [t for t in query.lower().replace("_", " ").split() if len(t) > 2]
    score = float(row.get("score") or 0) * 4.0
    score += sum(1.5 for t in tokens if t in blob)
    if must:
        score += 8.0
    return score


def pick_ranked(query: str, category: str = "", k: int = 4) -> list[dict]:
    """Rank PH /search hits with token overlap (Holodeck-style retrieval, no extra model)."""
    results = search(query, "models", limit=20)
    ranked = sorted(results, key=lambda r: _score(query, category, r), reverse=True)
    out = []
    for row in ranked:
        if _score(query, category, row) < 0:
            continue
        slug = row.get("slug") or ""
        pack = gltf_pack(files(slug))
        if not pack:
            continue
        out.append(
            {
                "catalog_id": "ph_" + slug,
                "ph_id": slug,
                "url": pack[0][1],
                "text": f"{slug} — CC0, Poly Haven",
                "real_size_m": size_m(slug),
                "score": _score(query, category, row),
            }
        )
        if len(out) >= k:
            break
    return out


def pick_model(query: str, index: int = 0, category: str = "") -> dict | None:
    ranked = pick_ranked(query, category=category, k=index + 1)
    if index < len(ranked):
        return ranked[index]
    return None


TEX_Q = {
    "grass": "grass ground",
    "dirt": "dirt ground",
    "sand": "sand",
    "pavement": "asphalt",
    "floor": "wood floor",
    "path": "asphalt",
    "trail": "dirt path",
    "wall": "plaster wall",
}


def _map_url(files_tree: dict, kind: str) -> str | None:
    block = files_tree.get(kind) or {}
    onek = block.get("1k") if isinstance(block, dict) else None
    if not isinstance(onek, dict):
        return None
    for fmt in ("jpg", "png"):
        item = onek.get(fmt)
        if isinstance(item, dict) and item.get("url"):
            return str(item["url"])
    return None


def pick_texture(kind: str) -> dict | None:
    q = TEX_Q.get(kind) or kind
    for row in search(q, "textures", limit=8):
        slug = row.get("slug")
        if not slug:
            continue
        files_tree = files(slug)
        diff = _map_url(files_tree, "Diffuse")
        if not diff:
            continue
        return {
            "catalog_id": "ph_tex_" + slug,
            "ph_id": slug,
            "diff_url": diff,
            "nor_url": _map_url(files_tree, "nor_gl"),
            "rough_url": _map_url(files_tree, "Rough"),
            "text": f"{slug} texture — CC0, Poly Haven",
        }
    return None


def pick_hdri(preset: str) -> dict | None:
    q = HDRI_Q.get(preset) or "outdoor sky"
    for row in search(q, "hdris", limit=8):
        slug = row.get("slug")
        if not slug:
            continue
        url = hdri_url(files(slug))
        if not url:
            continue
        return {
            "catalog_id": "ph_hdri_" + slug,
            "ph_id": slug,
            "url": url,
            "text": f"{slug} HDRI — CC0, Poly Haven",
        }
    return None
