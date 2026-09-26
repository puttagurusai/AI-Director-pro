"""Prompt → PlannerDraft when Groq is unset. Different text → different objects."""

from __future__ import annotations

import re

from app.ir.schema import (
    CameraDraft,
    Opening,
    PlannerDraft,
    Relation,
    SceneObjectDraft,
    WorldSpec,
)

WORLD = {
    "interior": WorldSpec(
        extent_x_m=10.0,
        extent_y_m=8.0,
        height_m=3.0,
        ground="floor",
        openings=[
            Opening(type="window", wall="wall.north", offset_m=3.0, width_m=2.2, sill_m=0.9, height_m=1.5),
            Opening(type="door", wall="wall.east", offset_m=0.5, width_m=0.95, sill_m=0.0, height_m=2.1),
        ],
    ),
    "park": WorldSpec(extent_x_m=48.0, extent_y_m=36.0, height_m=16.0, ground="grass"),
    "forest": WorldSpec(extent_x_m=55.0, extent_y_m=55.0, height_m=22.0, ground="dirt", terrain_amp_m=0.3),
    "city": WorldSpec(extent_x_m=48.0, extent_y_m=28.0, height_m=28.0, ground="pavement"),
    "zoo": WorldSpec(extent_x_m=42.0, extent_y_m=32.0, height_m=12.0, ground="dirt"),
    "space": WorldSpec(extent_x_m=28.0, extent_y_m=20.0, height_m=10.0, ground="metal_deck"),
    "beach": WorldSpec(extent_x_m=48.0, extent_y_m=32.0, height_m=12.0, ground="sand"),
    "generic": WorldSpec(extent_x_m=28.0, extent_y_m=28.0, height_m=10.0, ground="floor"),
}

BASE = {
    "interior": [("sofa_1", "sofa", "seat"), ("table_1", "coffee_table", "mass"), ("plant_1", "plant", "proxy_cylinder")],
    "park": [("path_1", "path", "slab"), ("tree_1", "tree", "foliage"), ("tree_2", "tree", "foliage"), ("bench_1", "bench", "seat")],
    "forest": [("tree_1", "tree", "foliage"), ("tree_2", "tree", "foliage"), ("tree_3", "tree", "foliage"), ("rock_1", "rock", "mass")],
    "city": [("street_1", "path", "slab"), ("bldg_1", "building_mass", "mass"), ("bldg_2", "building_mass", "mass"), ("lamp_1", "streetlamp", "pole")],
    "zoo": [("path_1", "path", "slab"), ("enc_1", "enclosure", "enclosure"), ("animal_1", "animal", "mass"), ("bench_1", "bench", "seat")],
    "space": [("mod_1", "module", "module"), ("crate_1", "crate", "mass"), ("ant_1", "antenna", "pole")],
    "beach": [("rock_1", "rock", "mass"), ("umb_1", "umbrella", "pole"), ("wood_1", "driftwood", "beam")],
    "generic": [("mass_1", "prop_a", "mass"), ("pole_1", "pole", "pole")],
}

EXTRA = [
    (r"\bsofas?\b", "sofa", "seat"),
    (r"\bchairs?\b", "dining_chair", "seat"),
    (r"\bdesks?\b", "desk", "mass"),
    (r"\bbeds?\b", "bed", "mass"),
    (r"\bplants?\b|\bflowers?\b", "plant", "proxy_cylinder"),
    (r"\btrees?\b|\bpines?\b|\boaks?\b", "tree", "foliage"),
    (r"\bbenches?\b", "bench", "seat"),
    (r"\bponds?\b|\blake\b", "pond", "puddle"),
    (r"\brocks?\b|\bboulders?\b", "rock", "mass"),
    (r"\blions?\b|\btigers?\b|\banimals?\b|\belephants?\b", "animal", "mass"),
    (r"\bcars?\b|\btrucks?\b|\bvehicles?\b", "vehicle", "mass"),
    (r"\blamps?\b|\blights?\b", "streetlamp", "pole"),
    (r"\bcrates?\b|\bboxes?\b", "crate", "mass"),
    (r"\bumbrellas?\b", "umbrella", "pole"),
    (r"\bbuildings?\b|\btowers?\b", "building_mass", "mass"),
    (r"\bfountains?\b", "fountain", "mass"),
    (r"\bmodules?\b|\bantennae?\b|\bantennas?\b", "module", "module"),
]

LIGHT = {
    "interior": "warm_interior",
    "park": "soft_day",
    "forest": "overcast",
    "city": "night_urban",
    "zoo": "soft_day",
    "space": "stars",
    "beach": "sunset",
    "generic": "high_key",
}


def _slug(word: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", word.lower()).strip("_")[:24]
    return s or "prop"


def plan_heuristic(domain: str, prompt: str) -> PlannerDraft:
    text = prompt or ""
    low = text.lower()
    world = WORLD.get(domain) or WORLD["generic"]
    seen: list[tuple[str, str, str]] = list(BASE.get(domain) or BASE["generic"])
    used_ids = {t[0] for t in seen}
    for i, (pat, cat, part) in enumerate(EXTRA):
        n = len(re.findall(pat, low))
        if n == 0:
            continue
        for k in range(max(1, min(n, 4))):
            oid = f"{cat}_{k+1}"
            if oid in used_ids:
                continue
            seen.append((oid, cat, part))
            used_ids.add(oid)
            if len(seen) >= 16:
                break
        if len(seen) >= 16:
            break
    objects = []
    for oid, cat, part in seen[:16]:
        rels: list[Relation] = []
        if domain == "interior" and cat in ("sofa", "bookshelf", "dresser", "bed"):
            rels.append(Relation(type="against_wall", target="wall.south"))
        if cat == "tree":
            rels.append(Relation(type="scatter", target="ground"))
        if cat == "bench" and "path_1" in used_ids:
            rels.append(Relation(type="along", target="path_1"))
        objects.append(
            SceneObjectDraft(id=_slug(oid), category=_slug(cat), part=part, relations=rels)
        )
    preset = LIGHT.get(domain, "soft_day")
    if re.search(r"\bsunset|dusk|evening\b", low):
        preset = "sunset"
    if re.search(r"\bnight|noir|dark\b", low):
        preset = "stars" if domain == "space" else "night_urban"
    look = objects[0].id if objects else None
    return PlannerDraft(
        domain=domain,  # type: ignore[arg-type]
        world=world,
        objects=objects,
        camera=CameraDraft(preset="wide_24", look_at_id=look),
        light_preset=preset,  # type: ignore[arg-type]
        notes="heuristic",
    )
