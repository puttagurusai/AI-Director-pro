"""Fill what the prompt omitted. Grass is LAND (texture), not a pile of grass meshes."""

from __future__ import annotations

# Surfaces the world always has, even if the user never said the word.
REQUIRED_GROUND = {
    "interior": "floor",
    "park": "grass",
    "forest": "dirt",
    "city": "pavement",
    "zoo": "dirt",
    "beach": "sand",
    "space": "pavement",
    "generic": "dirt",
}

# Minimum dressing counts. LLM list is the seed; we top up.
REQUIRED_COUNTS = {
    "park": {"path": 1, "tree": 36, "bench": 8, "bush": 14, "rock": 10, "streetlamp": 8},
    "forest": {"tree": 32, "bush": 12, "rock": 10},
    "city": {"path": 1, "building_mass": 6, "streetlamp": 8, "bench": 4},
    "zoo": {"path": 1, "enclosure": 2, "tree": 10, "bench": 4, "rock": 4, "animal": 2},
    "interior": {"sofa": 1, "coffee_table": 1, "plant": 2, "dining_chair": 2},
    "beach": {"rock": 8, "umbrella": 3, "bush": 6},
    "space": {"module": 3, "crate": 6},
    "generic": {},
}

PART_FOR = {
    "path": "slab",
    "tree": "foliage",
    "bush": "foliage",
    "rock": "mass",
    "bench": "seat",
    "streetlamp": "pole",
    "pond": "puddle",
    "plant": "proxy_cylinder",
    "sofa": "seat",
    "coffee_table": "mass",
    "dining_chair": "seat",
    "building_mass": "mass",
    "enclosure": "enclosure",
    "animal": "mass",
    "umbrella": "pole",
    "module": "module",
    "crate": "mass",
}


def apply_world_defaults(domain: str, world: dict) -> dict:
    world = dict(world)
    world["extent_x_m"] = min(250.0, max(4.0, float(world.get("extent_x_m") or 40)))
    world["extent_y_m"] = min(250.0, max(4.0, float(world.get("extent_y_m") or 40)))
    world["height_m"] = min(40.0, max(2.0, float(world.get("height_m") or 8)))
    world["terrain_amp_m"] = min(3.0, max(0.0, float(world.get("terrain_amp_m") or 0)))
    world["ground"] = REQUIRED_GROUND.get(domain, world.get("ground") or "grass")
    if domain in ("park", "forest", "zoo", "beach") and float(world.get("terrain_amp_m") or 0) < 0.4:
        world["terrain_amp_m"] = {"park": 1.2, "forest": 1.8, "zoo": 0.9, "beach": 0.7}.get(domain, 1.0)
    if domain == "interior":
        world["terrain_amp_m"] = 0.0
        world["ground"] = "floor"
    if domain == "city":
        world["ground"] = "pavement"
    return world


def fill_missing(domain: str, objects: list) -> list:
    """Top up required categories. Does not add 'grass' as a mesh — grass is the ground surface."""
    counts: dict[str, int] = {}
    out = [dict(o) for o in objects]
    for o in out:
        cat = o.get("category") or ""
        counts[cat] = counts.get(cat, 0) + 1
    need = REQUIRED_COUNTS.get(domain) or {}
    for cat, n in need.items():
        have = counts.get(cat, 0)
        part = PART_FOR.get(cat, "mass")
        for i in range(have + 1, n + 1):
            oid = f"{cat}_{i}"
            rel = []
            if cat == "bench":
                rel = [{"type": "along", "target": "path_1", "clearance_m": 0.4}]
            elif cat in ("tree", "bush", "rock"):
                rel = [{"type": "scatter", "target": "ground", "clearance_m": 1.2}]
            out.append(
                {
                    "id": oid,
                    "category": cat,
                    "part": part,
                    "relations": rel,
                    "style_tags": [],
                }
            )
        counts[cat] = max(have, n)
    return out
