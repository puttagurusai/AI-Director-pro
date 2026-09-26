"""In-addon planner: Groq + Poly Haven. No local server."""

from __future__ import annotations

import json
import math
import re
import time
import urllib.request
import uuid

from . import polyhaven as ph
from .catalog_index import hits_for_slugs, sample_hdri, sample_slugs, sample_texture
from .completeness import apply_world_defaults, fill_missing
from .layout import pack_scene
from .logutil import log

from .groq_client import chat as groq_chat, load_config as groq_config
PH_UA = "AIDirector/0.1 (+local ingest; https://polyhaven.com/our-api)"
PH_BASE = "https://api.polyhaven.com"

KEYWORDS = (
    ("space", ("space", "orbit", "station", "planet", "nasa", "spaceship")),
    ("zoo", ("zoo", "safari", "enclosure", "habitat", "lion", "tiger")),
    ("forest", ("forest", "woods", "jungle", "clearing")),
    ("park", ("park", "playground", "garden", "pond", "bench")),
    ("city", ("city", "street", "downtown", "alley", "skyscraper")),
    ("beach", ("beach", "shore", "ocean", "sand", "umbrella")),
    ("interior", ("living room", "bedroom", "office", "kitchen", "interior", "apartment", "sofa")),
)

WORLD = {
    "interior": {"extent_x_m": 10.0, "extent_y_m": 8.0, "height_m": 3.0, "wall_thickness_m": 0.15,
                 "openings": [
                     {"type": "window", "wall": "wall.north", "offset_m": 3.0, "width_m": 2.2, "sill_m": 0.9, "height_m": 1.5},
                     {"type": "door", "wall": "wall.east", "offset_m": 0.5, "width_m": 0.95, "sill_m": 0.0, "height_m": 2.1},
                 ], "ground": "floor", "terrain_amp_m": 0.0},
    "park": {"extent_x_m": 140.0, "extent_y_m": 100.0, "height_m": 24.0, "wall_thickness_m": 0.15, "openings": [], "ground": "grass", "terrain_amp_m": 1.4},
    "forest": {"extent_x_m": 160.0, "extent_y_m": 160.0, "height_m": 28.0, "wall_thickness_m": 0.15, "openings": [], "ground": "dirt", "terrain_amp_m": 2.0},
    "city": {"extent_x_m": 64.0, "extent_y_m": 40.0, "height_m": 30.0, "wall_thickness_m": 0.15, "openings": [], "ground": "pavement", "terrain_amp_m": 0.15},
    "zoo": {"extent_x_m": 60.0, "extent_y_m": 48.0, "height_m": 14.0, "wall_thickness_m": 0.15, "openings": [], "ground": "dirt", "terrain_amp_m": 0.9},
    "space": {"extent_x_m": 28.0, "extent_y_m": 20.0, "height_m": 10.0, "wall_thickness_m": 0.15, "openings": [], "ground": "metal_deck", "terrain_amp_m": 0.0},
    "beach": {"extent_x_m": 72.0, "extent_y_m": 48.0, "height_m": 14.0, "wall_thickness_m": 0.15, "openings": [], "ground": "sand", "terrain_amp_m": 0.7},
    "generic": {"extent_x_m": 28.0, "extent_y_m": 28.0, "height_m": 10.0, "wall_thickness_m": 0.15, "openings": [], "ground": "floor", "terrain_amp_m": 0.0},
}

def _many(prefix, cat, part, n):
    return [(f"{prefix}_{i+1}", cat, part) for i in range(n)]


DENSE = {
    "interior": [
        ("sofa_1", "sofa", "seat"), ("table_1", "coffee_table", "mass"),
        ("chair_1", "dining_chair", "seat"), ("chair_2", "dining_chair", "seat"),
        ("plant_1", "plant", "proxy_cylinder"), ("plant_2", "plant", "proxy_cylinder"),
        ("shelf_1", "bookshelf", "mass"), ("lamp_1", "lamp_floor", "pole"),
        ("rug_1", "rug", "slab"), ("side_1", "side_table", "mass"),
    ],
    "park": (
        [("path_1", "path", "slab"), ("pond_1", "pond", "puddle")]
        + _many("tree", "tree", "foliage", 40)
        + _many("bench", "bench", "seat", 6)
        + _many("rock", "rock", "mass", 10)
        + _many("bush", "bush", "foliage", 12)
        + _many("lamp", "streetlamp", "pole", 6)
    ),
    "forest": _many("tree", "tree", "foliage", 36) + _many("rock", "rock", "mass", 12) + _many("bush", "bush", "foliage", 14),
    "city": (
        [("street_1", "path", "slab")]
        + _many("bldg", "building_mass", "mass", 6)
        + _many("lamp", "streetlamp", "pole", 8)
        + _many("bench", "bench", "seat", 4)
        + [("car_1", "vehicle", "mass"), ("car_2", "vehicle", "mass")]
    ),
    "zoo": (
        [("path_1", "path", "slab"), ("enc_1", "enclosure", "enclosure"), ("enc_2", "enclosure", "enclosure"),
         ("animal_1", "animal", "mass"), ("animal_2", "animal", "mass")]
        + _many("tree", "tree", "foliage", 10)
        + _many("bench", "bench", "seat", 4)
        + _many("rock", "rock", "mass", 4)
    ),
    "space": _many("mod", "module", "module", 4) + _many("crate", "crate", "mass", 8) + _many("ant", "antenna", "pole", 3),
    "beach": _many("rock", "rock", "mass", 8) + _many("umb", "umbrella", "pole", 4) + _many("bush", "bush", "foliage", 6) + [("wood_1", "driftwood", "beam"), ("wood_2", "driftwood", "beam")],
    "generic": _many("mass", "mass", "mass", 8) + _many("pole", "pole", "pole", 4),
}

EXTRA = [
    (r"\bsofas?\b", "sofa", "seat"),
    (r"\bchairs?\b", "dining_chair", "seat"),
    (r"\bdesks?\b", "desk", "mass"),
    (r"\bbeds?\b", "bed", "mass"),
    (r"\bplants?\b|\bflowers?\b", "plant", "proxy_cylinder"),
    (r"\btrees?\b|\bpines?\b", "tree", "foliage"),
    (r"\bbenches?\b", "bench", "seat"),
    (r"\bponds?\b|\blake\b", "pond", "puddle"),
    (r"\brocks?\b", "rock", "mass"),
    (r"\blions?\b|\btigers?\b|\banimals?\b", "animal", "mass"),
    (r"\bcars?\b|\bvehicles?\b", "vehicle", "mass"),
    (r"\blamps?\b", "streetlamp", "pole"),
    (r"\bcrates?\b", "crate", "mass"),
    (r"\bumbrellas?\b", "umbrella", "pole"),
    (r"\bbuildings?\b", "building_mass", "mass"),
]

LIGHT = {
    "interior": "warm_interior", "park": "soft_day", "forest": "overcast",
    "city": "night_urban", "zoo": "soft_day", "space": "stars",
    "beach": "sunset", "generic": "high_key",
}

SIZES = {
    "sofa": (2.1, 0.9, 0.85), "coffee_table": (1.2, 0.6, 0.4), "plant": (0.45, 0.45, 1.2),
    "tree": (3.5, 3.5, 9.0), "bush": (1.4, 1.4, 1.6), "bench": (1.8, 0.55, 0.9),
    "path": (4.0, 30.0, 0.08), "rock": (1.8, 1.4, 1.0), "building_mass": (10, 8, 16),
    "streetlamp": (0.25, 0.25, 5.0), "enclosure": (8, 10, 3.5), "animal": (2.4, 0.9, 1.3),
    "module": (5, 5, 3.5), "crate": (1.2, 1.2, 1.2), "antenna": (0.3, 0.3, 6),
    "pond": (8, 5, 0.06), "umbrella": (2.0, 2.0, 2.4), "driftwood": (2.2, 0.45, 0.35),
    "desk": (1.4, 0.7, 0.75), "dining_chair": (0.5, 0.55, 0.95), "bookshelf": (0.9, 0.35, 1.8),
    "lamp_floor": (0.35, 0.35, 1.6), "rug": (2.6, 1.8, 0.03), "side_table": (0.5, 0.5, 0.55),
    "vehicle": (4.2, 1.8, 1.5),
}

# Architecture we still build procedurally (not a PH mesh).
# Built as kits (no PH mesh required). Everything else is skipped if no catalog hit.
SKIP_PH = {"path", "building_mass", "enclosure", "planet", "rug"}
KEEP_WITHOUT_MODEL = {"path", "building_mass", "enclosure"}

SYSTEM = """You are a film production designer. Mentally picture the COMPLETE place from the sentence, then list every object that would be in that picture — even if the user did not name it (grass is the GROUND, not an object; still list path, trees, benches, lamps, rocks, shrubs, water, furniture).
Reply with ONE JSON object, no markdown.
Use RELATIONS (no world xyz): along, next_to, in_front_of, facing, scatter, against_wall, on.
{"schema_version":"0.1","domain":"<DOMAIN>","world":{"extent_x_m":n,"extent_y_m":n,"height_m":n,"wall_thickness_m":0.15,"openings":[],"ground":"floor|grass|dirt|pavement|sand|metal_deck","terrain_amp_m":0.8},
"objects":[{"id":"snake","category":"tree|bench|rock|bush|sofa|plant|path|streetlamp","part":"foliage|seat|mass|slab|pole","relations":[{"type":"along|scatter|next_to|facing|against_wall|on","target":"path_1|ground|<id>","clearance_m":0.4}],"style_tags":[]}],
"camera":{"preset":"wide_24","look_at_id":"<id>"},"light_preset":"soft_day|warm_interior|sunset|night_urban|stars|overcast","notes":""}
Rules: 20-40 objects. One path/street only. Park/forest: many scatter trees. Benches along the path facing it. terrain_amp_m 0.8-1.8 outdoors, 0 interior. No xyz, no Python, no URLs. domain MUST match DOMAIN."""

_status = {"online": False, "key": "", "checked": 0.0, "detail": "no key"}


def infer_domain(ui: str, prompt: str) -> str:
    if ui and ui != "auto":
        return ui
    text = (prompt or "").lower()
    for domain, keys in KEYWORDS:
        if any(k in text for k in keys):
            return domain
    return "generic"


def groq_status(api_key: str) -> str:
    from .groq_client import ping as groq_ping

    key = (api_key or "").strip()
    now = time.time()
    if not key:
        _status.update(online=False, key="", detail="no key")
        return "offline"
    if _status["key"] == key and now - _status["checked"] < 60:
        return "online" if _status["online"] else "offline"
    state, detail = groq_ping(key)
    _status.update(online=state == "online", key=key, checked=now, detail=detail)
    return state


def _http_json(url: str, headers=None, data=None, timeout=40):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": PH_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b <= a:
        raise RuntimeError("Groq returned no JSON")
    return json.loads(raw[a : b + 1])


def _groq_draft(domain: str, prompt: str, api_key: str, randomness: float = 0.5) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM.replace("<DOMAIN>", domain)},
        {
            "role": "user",
            "content": (
                f"DOMAIN={domain}\nPROMPT={prompt.strip() or 'a simple scene'}\n"
                "Imagine the finished picture. List ALL objects that belong there "
                "(counts included). Relations required. Do not omit dressing."
            ),
        },
    ]
    temp = 0.12 + 0.7 * max(0.0, min(1.0, randomness))
    try:
        body = groq_chat(api_key, messages, json_object=True, max_tokens=2500, temperature=temp)
    except Exception:
        body = groq_chat(api_key, messages, json_object=False, max_tokens=2500, temperature=temp)
    draft = _extract_json(body["choices"][0]["message"]["content"])
    draft["domain"] = domain
    return draft


def _heuristic_draft(domain: str, prompt: str) -> dict:
    low = (prompt or "").lower()
    world = dict(WORLD.get(domain) or WORLD["generic"])
    seen = list(DENSE.get(domain) or DENSE["generic"])
    used = {t[0] for t in seen}
    for pat, cat, part in EXTRA:
        if not re.search(pat, low):
            continue
        for k in range(1, 5):
            oid = f"{cat}_{k}"
            if oid not in used:
                seen.append((oid, cat, part))
                used.add(oid)
                break
    objects = [{"id": oid, "category": cat, "part": part, "relations": [], "style_tags": []} for oid, cat, part in seen[:48]]
    preset = LIGHT.get(domain, "soft_day")
    if re.search(r"sunset|dusk|evening", low):
        preset = "sunset"
    if re.search(r"\bnight|dark\b", low):
        preset = "stars" if domain == "space" else "night_urban"
    return {
        "schema_version": "0.1",
        "domain": domain,
        "world": world,
        "objects": objects,
        "camera": {"preset": "wide_24", "look_at_id": objects[0]["id"] if objects else None},
        "light_preset": preset,
        "notes": "heuristic",
    }


def _dedupe_shells(objects: list) -> list:
    """One path / pond / street only — Groq often emits four overlapping paths."""
    once = {"path", "pond"}
    seen = set()
    out = []
    for o in objects:
        cat = o.get("category")
        if cat in once:
            if cat in seen:
                continue
            seen.add(cat)
            o = dict(o)
            o["id"] = cat + "_1"
        out.append(o)
    return out


def _merge_density(domain: str, objects: list) -> list:
    have = {o.get("id") for o in objects}
    out = list(objects)
    for oid, cat, part in DENSE.get(domain) or []:
        if oid in have:
            continue
        out.append({"id": oid, "category": cat, "part": part, "relations": [], "style_tags": []})
        have.add(oid)
        if len(out) >= 80:
            break
    return out


def _size(cat: str, part: str):
    if cat in SIZES:
        return SIZES[cat]
    return {"slab": (4, 2, 0.08), "foliage": (2, 2, 5), "mass": (1, 1, 1)}.get(part, (1, 1, 1))


def _pose(x, y, z=0.0, yaw=0.0):
    return {
        "location_m": [round(x, 3), round(y, 3), z],
        "rotation_euler_rad": [0.0, 0.0, yaw],
        "scale": [1, 1, 1],
        "support": "ground",
        "snap_z_pending": True,
        "infeasibility": None,
    }


def _pack(objects: list, world: dict) -> dict:
    wx, wy = float(world["extent_x_m"]), float(world["extent_y_m"])
    by = {}
    for o in objects:
        by.setdefault(o["category"], []).append(o)
    poses = {}
    if "path" in by:
        for o in by["path"]:
            poses[o["id"]] = _pose(wx / 2.0, wy / 2.0)
            o["real_size_m"] = [max(3.5, wx * 0.12), wy * 0.82, 0.08]
    trees = by.get("tree") or []
    for i, o in enumerate(trees):
        ang = (2 * math.pi * i / max(1, len(trees))) + 0.2
        radx, rady = wx * 0.38, wy * 0.38
        poses[o["id"]] = _pose(wx / 2 + radx * math.cos(ang), wy / 2 + rady * math.sin(ang), yaw=ang)
    bushes = by.get("bush") or []
    for i, o in enumerate(bushes):
        ang = 2 * math.pi * i / max(1, len(bushes)) + 1.1
        poses[o["id"]] = _pose(wx / 2 + wx * 0.28 * math.cos(ang), wy / 2 + wy * 0.28 * math.sin(ang))
    rocks = by.get("rock") or []
    for i, o in enumerate(rocks):
        poses[o["id"]] = _pose(wx * (0.18 + 0.12 * (i % 5)), wy * (0.2 + 0.14 * (i // 5)))
    benches = by.get("bench") or []
    for i, o in enumerate(benches):
        y = wy * (0.25 + 0.5 * (i / max(1, len(benches) - 1 or 1)))
        x = wx / 2.0 + (2.4 if i % 2 == 0 else -2.4)
        poses[o["id"]] = _pose(x, y, yaw=1.5708 if i % 2 == 0 else -1.5708)
    lamps = by.get("streetlamp") or []
    for i, o in enumerate(lamps):
        poses[o["id"]] = _pose(wx / 2 + (3.2 if i % 2 == 0 else -3.2), wy * (0.15 + 0.7 * i / max(1, len(lamps))))
    bldgs = by.get("building_mass") or []
    for i, o in enumerate(bldgs):
        side = -1 if i % 2 == 0 else 1
        poses[o["id"]] = _pose(wx / 2 + side * wx * 0.32, wy * (0.18 + 0.14 * (i // 2)))
    rest = [o for o in objects if o["id"] not in poses]
    for i, o in enumerate(rest):
        poses[o["id"]] = _pose(wx * (0.22 + 0.15 * (i % 5)), wy * (0.22 + 0.15 * (i // 5)))
    return poses


def _camera(world, poses):
    wx, wy = float(world["extent_x_m"]), float(world["extent_y_m"])
    # Eye-level on the path, looking into the set — not an aerial zoom-out.
    return {
        "location_m": [wx * 0.50, 5.0, 1.8],
        "look_at_m": [wx * 0.50, wy * 0.72, 1.4],
        "focal_mm": 28.0,
    }


def _stamp_assets(objects: list, seed: str = "scene", randomness: float = 0.5) -> tuple[list, list, list]:
    """Sample unique PH meshes from the full 500+ index, then instance extras."""
    import random as _rnd

    r = max(0.0, min(1.0, float(randomness)))
    rng = _rnd.Random((abs(hash(seed)) % (2**31)) ^ int(r * 99991))
    counts: dict[str, int] = {}
    for spec in objects:
        cat = spec.get("category") or "mass"
        counts[cat] = counts.get(cat, 0) + 1
    sampled: dict[str, list] = {}
    for cat, n in counts.items():
        if cat in SKIP_PH:
            continue
        slugs = sample_slugs(cat, n, rng)
        hits = hits_for_slugs(slugs) if slugs else []
        if not hits:
            q = ph.SEARCH_Q.get(cat) or cat.replace("_", " ")
            try:
                hits = ph.pick_ranked(q, category=cat, k=min(4, n))
            except Exception:
                hits = []
        sampled[cat] = hits
        log(f"sample {cat}: need={n} unique_hits={len({h['ph_id'] for h in hits})}")
    out, fallbacks, attrib = [], [], []
    seen_attr = set()
    used: dict[str, int] = {}
    for spec in objects:
        cat = spec.get("category") or "mass"
        size = list(spec.get("real_size_m") or _size(cat, spec.get("part") or "mass"))
        catalog_id = asset_url = license_ = None
        pool = sampled.get(cat) or []
        if pool:
            i = used.get(cat, 0)
            hit = pool[i % len(pool)]
            used[cat] = i + 1
            catalog_id, asset_url, license_ = hit["catalog_id"], hit["url"], "CC0"
            if hit.get("real_size_m"):
                size = list(hit["real_size_m"])
            if catalog_id not in seen_attr:
                attrib.append({"catalog_id": catalog_id, "license": "CC0", "text": hit["text"]})
                seen_attr.add(catalog_id)
        if not catalog_id:
            fallbacks.append({"object_id": spec["id"], "reason": "no_catalog_hit", "primitive": spec.get("part") or "mass"})
        out.append({
            "id": spec["id"],
            "category": cat,
            "part": spec.get("part") or "mass",
            "relations": spec.get("relations") or [],
            "style_tags": spec.get("style_tags") or [],
            "catalog_id": catalog_id,
            "license": license_,
            "real_size_m": size,
            "asset_url": asset_url,
        })
    return out, fallbacks, attrib


def build_scene(prompt: str, ui_domain: str, groq_key: str, randomness: float = 0.5) -> dict:
    domain = infer_domain(ui_domain, prompt)
    source = "heuristic"
    key = (groq_key or "").strip()
    draft = None
    if key:
        try:
            draft = _groq_draft(domain, prompt, key, randomness=randomness)
            source = "groq"
            _status.update(online=True, key=key, checked=time.time(), detail="ok")
        except Exception as exc:
            _status.update(online=False, key=key, checked=time.time(), detail=str(exc)[:80])
            draft = None
    if draft is None:
        draft = _heuristic_draft(domain, prompt)
    world = dict(WORLD.get(domain) or WORLD["generic"])
    incoming = draft.get("world") or {}
    if isinstance(incoming, dict):
        for k in ("ground", "openings", "terrain_amp_m", "wall_thickness_m"):
            if k in incoming:
                world[k] = incoming[k]
    world = apply_world_defaults(domain, world)
    log(f"world clamped {domain} {world['extent_x_m']}x{world['extent_y_m']} ground={world.get('ground')}")
    objects = draft.get("objects") or []
    objects = _dedupe_shells(objects)
    objects = _merge_density(domain, objects)
    objects = fill_missing(domain, objects)
    objects = _dedupe_shells(objects)
    objects, fallbacks, attrib = _stamp_assets(objects, seed=prompt or domain, randomness=randomness)
    kept, skipped = [], []
    for o in objects:
        if o.get("catalog_id") or o.get("category") in KEEP_WITHOUT_MODEL:
            kept.append(o)
        else:
            skipped.append(o.get("id"))
    if skipped:
        log(f"skip no-model {skipped}")
    objects = kept
    layout = pack_scene(objects, world, domain, randomness=randomness)
    log(f"domain={domain} source={source} n={len(objects)} ph={sum(1 for o in objects if o.get('catalog_id'))}")
    for o in objects:
        pose = layout.get(o["id"]) or {}
        loc = pose.get("location_m")
        log(f"  {o['id']:16} cat={o.get('category'):12} ph={o.get('catalog_id') or '-':22} size={o.get('real_size_m')} xyz={loc}")
    log(f"unresolved={[i for i,p in layout.items() if p.get('infeasibility')]}")
    preset = draft.get("light_preset") or LIGHT.get(domain, "soft_day")
    rng_look = __import__("random").Random((abs(hash(prompt or domain)) % (2**31)) ^ int(float(randomness) * 99991))
    hdri = None
    try:
        h = sample_hdri(preset, rng_look)
        if h:
            hdri = {"catalog_id": h["catalog_id"], "intensity": 1.0, "rotation_z": 0.0, "asset_url": h["url"]}
            attrib.append({"catalog_id": h["catalog_id"], "license": "CC0", "text": h["text"]})
    except Exception:
        hdri = None
    surfaces = {}
    ground_key = {
        "interior": "floor",
        "park": "grass",
        "forest": "dirt",
        "city": "pavement",
        "zoo": "dirt",
        "beach": "sand",
        "space": "pavement",
        "generic": "dirt",
    }.get(domain, "grass")
    path_key = "path" if domain == "city" else ("trail" if domain in ("park", "zoo") else None)
    wall_key = "wall" if domain == "interior" else None
    for kind, name in (("ground", ground_key), ("path", path_key), ("wall", wall_key)):
        if not name:
            continue
        try:
            tex = sample_texture(name, rng_look)
        except Exception:
            tex = None
        if tex:
            surfaces[kind] = tex
            attrib.append({"catalog_id": tex["catalog_id"], "license": "CC0", "text": tex["text"]})
    lights = [
        {"role": "sun", "type": "SUN", "energy": 4.0, "color_temp_k": 5500, "offset_from_camera_m": [2.0, 3.0, 4.0]},
        {"role": "fill", "type": "AREA", "energy": 40, "color_temp_k": 5000, "offset_from_camera_m": [-1.5, 0.2, 0.4]},
    ]
    return {
        "schema_version": "0.1",
        "job_id": uuid.uuid4().hex,
        "prompt": prompt or "",
        "domain": domain,
        "world": world,
        "objects": objects,
        "layout": layout,
        "camera": draft.get("camera") or {"preset": "wide_24", "look_at_id": None},
        "camera_pose": _camera(world, layout),
        "lights": lights,
        "hdri": hdri,
        "surfaces": surfaces,
        "light_preset": preset,
        "fallbacks": fallbacks,
        "warnings": [f"planner:{source}", "Powered by Poly Haven"],
        "attribution": attrib,
        "status": "ready",
    }
