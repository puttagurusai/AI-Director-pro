"""Generate Phase 0 bundled SceneIR fixtures. Run from backend root: python scripts/write_fixtures.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ir.schema import SceneIR, default_size  # noqa: E402

ADDON_FIXTURES = ROOT.parent / "fixtures"
BACKEND_FIXTURES = ROOT / "fixtures"


def pose(xyz, yaw=0.0, support="ground", snap=True):
    return {
        "location_m": [round(xyz[0], 4), round(xyz[1], 4), round(xyz[2], 4)],
        "rotation_euler_rad": [0.0, 0.0, round(yaw, 4)],
        "scale": [1.0, 1.0, 1.0],
        "support": support,
        "snap_z_pending": snap,
        "infeasibility": None,
    }


def obj(oid, category, part, size=None, relations=None, **extra):
    sx, sy, sz = size or default_size(category, part)
    d = {
        "id": oid,
        "category": category,
        "part": part,
        "relations": relations or [],
        "style_tags": [],
        "catalog_id": None,
        "license": None,
        "real_size_m": [sx, sy, sz],
    }
    d.update(extra)
    return d


def lights_cam(offsets=None):
    return [
        {
            "role": "key",
            "type": "AREA",
            "energy": 250,
            "color_temp_k": 4500,
            "offset_from_camera_m": [1.2, 0.4, 0.8],
        },
        {
            "role": "fill",
            "type": "AREA",
            "energy": 80,
            "color_temp_k": 5000,
            "offset_from_camera_m": [-1.5, 0.2, 0.4],
        },
        {
            "role": "rim",
            "type": "AREA",
            "energy": 40,
            "color_temp_k": 5500,
            "offset_from_camera_m": [0.0, 0.3, 1.2],
        },
    ]


def wrap(
    job_id,
    prompt,
    domain,
    world,
    objects,
    layout,
    camera,
    camera_pose,
    light_preset,
    warnings=None,
):
    fallbacks = [
        {"object_id": o["id"], "reason": "no_catalog_hit", "primitive": o["part"]}
        for o in objects
    ]
    doc = {
        "schema_version": "0.1",
        "job_id": job_id,
        "prompt": prompt,
        "domain": domain,
        "world": world,
        "objects": objects,
        "layout": layout,
        "camera": camera,
        "camera_pose": camera_pose,
        "lights": lights_cam(),
        "hdri": None,
        "light_preset": light_preset,
        "fallbacks": fallbacks,
        "warnings": warnings or ["phase0:primitives_only"],
        "attribution": [],
        "status": "ready",
    }
    SceneIR.model_validate(doc)
    return doc


def living_room():
    world = {
        "extent_x_m": 5.5,
        "extent_y_m": 4.2,
        "height_m": 2.7,
        "wall_thickness_m": 0.15,
        "openings": [
            {
                "type": "window",
                "wall": "wall.north",
                "offset_m": 1.6,
                "width_m": 1.8,
                "sill_m": 0.9,
                "height_m": 1.4,
            },
            {
                "type": "door",
                "wall": "wall.east",
                "offset_m": 0.4,
                "width_m": 0.9,
                "sill_m": 0.0,
                "height_m": 2.1,
            },
        ],
        "ground": "floor",
        "terrain_amp_m": 0.0,
    }
    objects = [
        obj(
            "rug_1",
            "rug",
            "slab",
            (2.4, 1.6, 0.02),
            [{"type": "centered_on", "target": "floor", "clearance_m": 0.0}],
        ),
        obj(
            "sofa_1",
            "sofa",
            "seat",
            (1.57, 0.66, 0.80),
            [
                {"type": "against_wall", "target": "wall.south", "clearance_m": 0.08},
                {"type": "facing", "target": "wall.north", "clearance_m": 0.0},
            ],
        ),
        obj(
            "table_1",
            "coffee_table",
            "mass",
            (1.54, 0.97, 0.52),
            [{"type": "in_front_of", "target": "sofa_1", "clearance_m": 0.45}],
        ),
        obj(
            "plant_1",
            "plant",
            "proxy_cylinder",
            (0.45, 0.45, 1.2),
            [{"type": "next_to", "target": "sofa_1", "clearance_m": 0.2}],
        ),
        obj("plant_2", "plant", "proxy_cylinder", (0.45, 0.45, 1.1)),
        obj(
            "armchair_1",
            "armchair",
            "seat",
            (0.85, 0.85, 0.90),
            [{"type": "against_wall", "target": "wall.west", "clearance_m": 0.08}],
        ),
        obj("lamp_1", "lamp_floor", "pole", (0.30, 0.30, 1.50)),
        obj(
            "shelf_1",
            "bookshelf",
            "mass",
            (0.80, 0.30, 1.80),
            [{"type": "against_wall", "target": "wall.west", "clearance_m": 0.08}],
        ),
        obj(
            "art_1",
            "art_frame",
            "board",
            (0.70, 0.04, 0.90),
            [{"type": "against_wall", "target": "wall.north", "clearance_m": 0.05}],
        ),
        obj("ottoman_1", "ottoman", "mass", (0.80, 0.60, 0.40)),
        obj("chair_1", "dining_chair", "seat", (0.50, 0.55, 0.95)),
        obj("chair_2", "dining_chair", "seat", (0.50, 0.55, 0.95)),
        obj("stool_1", "stool", "mass", (0.40, 0.40, 0.45)),
        obj("side_1", "side_table", "mass", (0.45, 0.45, 0.55)),
        obj(
            "dresser_1",
            "dresser",
            "mass",
            (1.20, 0.50, 0.80),
            [{"type": "against_wall", "target": "wall.east", "clearance_m": 0.08}],
        ),
    ]
    layout = {
        "rug_1": pose((2.75, 2.10, 0.0), support="floor"),
        "sofa_1": pose((2.75, 0.41, 0.0), support="floor"),
        "table_1": pose((2.75, 1.675, 0.0), support="floor"),
        "plant_1": pose((3.96, 0.41, 0.0), support="floor"),
        "plant_2": pose((1.54, 0.41, 0.0), support="floor"),
        "armchair_1": pose((0.505, 2.40, 0.0), yaw=1.5708, support="floor"),
        "lamp_1": pose((1.20, 2.40, 0.0), support="floor"),
        "shelf_1": pose((0.23, 3.55, 0.0), yaw=1.5708, support="floor"),
        "art_1": pose((2.75, 4.13, 1.4), yaw=3.1416, support="wall.north", snap=False),
        "ottoman_1": pose((1.55, 1.70, 0.0), support="floor"),
        "chair_1": pose((4.40, 2.40, 0.0), support="floor"),
        "chair_2": pose((4.40, 3.20, 0.0), support="floor"),
        "stool_1": pose((3.70, 3.50, 0.0), support="floor"),
        "side_1": pose((4.30, 0.50, 0.0), support="floor"),
        "dresser_1": pose((5.17, 2.80, 0.0), yaw=-1.5708, support="floor"),
    }
    return wrap(
        "01jfix01livingroom000000000000",
        "Small modern living room, sofa facing a window, plant next to the sofa, coffee table in front, warm evening.",
        "interior",
        world,
        objects,
        layout,
        {"preset": "establishing_35", "look_at_id": "sofa_1"},
        {"location_m": [0.70, 3.70, 1.60], "look_at_m": [2.75, 0.41, 0.40], "focal_mm": 35.0},
        "warm_interior",
    )


def park():
    world = {
        "extent_x_m": 40.0,
        "extent_y_m": 30.0,
        "height_m": 12.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "grass",
        "terrain_amp_m": 0.0,
    }
    objects = [
        obj("path_1", "path", "slab", (24.0, 2.4, 0.08)),
        obj("tree_1", "tree", "foliage", relations=[{"type": "scatter", "target": "ground", "clearance_m": 1.5}]),
        obj("tree_2", "tree", "foliage", relations=[{"type": "scatter", "target": "ground", "clearance_m": 1.5}]),
        obj("tree_3", "tree", "foliage", relations=[{"type": "scatter", "target": "ground", "clearance_m": 1.5}]),
        obj("tree_4", "tree", "foliage", relations=[{"type": "scatter", "target": "ground", "clearance_m": 1.5}]),
        obj("bench_1", "bench", "seat", relations=[{"type": "along", "target": "path_1", "clearance_m": 0.35}]),
        obj("bench_2", "bench", "seat", relations=[{"type": "along", "target": "path_1", "clearance_m": 0.35}]),
        obj("pond_1", "pond", "puddle", relations=[{"type": "centered_on", "target": "ground", "clearance_m": 0.0}]),
        obj("lamp_1", "streetlamp", "pole"),
        obj("lamp_2", "streetlamp", "pole"),
        obj("rock_1", "rock", "mass"),
        obj("bush_1", "bush", "foliage", (1.2, 1.2, 1.4)),
    ]
    layout = {
        "path_1": pose((20.0, 15.0, 0.0)),
        "tree_1": pose((6.0, 6.0, 0.0)),
        "tree_2": pose((34.0, 7.0, 0.0)),
        "tree_3": pose((8.0, 24.0, 0.0)),
        "tree_4": pose((32.0, 24.0, 0.0)),
        "bench_1": pose((20.0, 16.85, 0.0)),
        "bench_2": pose((20.0, 13.15, 0.0), yaw=3.1416),
        "pond_1": pose((10.0, 10.0, 0.0)),
        "lamp_1": pose((8.5, 15.0, 0.0)),
        "lamp_2": pose((31.5, 15.0, 0.0)),
        "rock_1": pose((12.0, 22.0, 0.0)),
        "bush_1": pose((28.0, 8.0, 0.0)),
    }
    return wrap(
        "01jfix01park000000000000000000",
        "Park at dusk, a path, benches, trees, and a pond.",
        "park",
        world,
        objects,
        layout,
        {"preset": "establishing_35", "look_at_id": "path_1"},
        {"location_m": [4.0, 4.0, 1.6], "look_at_m": [20.0, 15.0, 0.4], "focal_mm": 35.0},
        "sunset",
    )


def forest():
    world = {
        "extent_x_m": 50.0,
        "extent_y_m": 50.0,
        "height_m": 20.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "dirt",
        "terrain_amp_m": 0.25,
    }
    objects = [
        obj(f"tree_{i}", "tree", "foliage", relations=[{"type": "scatter", "target": "ground", "clearance_m": 2.0}])
        for i in range(1, 9)
    ] + [
        obj("rock_1", "rock", "mass"),
        obj("rock_2", "rock", "mass"),
        obj("log_1", "log", "beam"),
        obj("bush_1", "bush", "foliage"),
    ]
    coords = [
        (8, 8), (18, 10), (30, 8), (42, 12),
        (10, 28), (22, 32), (36, 26), (44, 40),
        (16, 20), (28, 18), (20, 40), (38, 36),
    ]
    layout = {o["id"]: pose((coords[i][0], coords[i][1], 0.0)) for i, o in enumerate(objects)}
    return wrap(
        "01jfix01forest0000000000000000",
        "Forest clearing, wet ground, logs, dense trees.",
        "forest",
        world,
        objects,
        layout,
        {"preset": "wide_24", "look_at_id": "log_1"},
        {"location_m": [5.0, 5.0, 1.8], "look_at_m": [25.0, 25.0, 1.0], "focal_mm": 24.0},
        "overcast",
    )


def city():
    world = {
        "extent_x_m": 40.0,
        "extent_y_m": 24.0,
        "height_m": 30.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "pavement",
        "terrain_amp_m": 0.0,
    }
    objects = [
        obj("street_1", "path", "slab", (36.0, 8.0, 0.10)),
        obj("walk_w", "sidewalk", "slab", (36.0, 3.0, 0.08)),
        obj("walk_e", "sidewalk", "slab", (36.0, 3.0, 0.08)),
        obj("bldg_1", "building_mass", "mass", (10.0, 8.0, 14.0)),
        obj("bldg_2", "building_mass", "mass", (12.0, 8.0, 18.0)),
        obj("lamp_1", "streetlamp", "pole"),
        obj("lamp_2", "streetlamp", "pole"),
        obj("lamp_3", "streetlamp", "pole"),
        obj("sign_1", "sign", "board"),
        obj("car_1", "vehicle", "mass"),
        obj("kiosk_1", "kiosk", "mass"),
        obj("bench_1", "bench", "seat"),
    ]
    layout = {
        "street_1": pose((20.0, 12.0, 0.0)),
        "walk_w": pose((20.0, 4.5, 0.0)),
        "walk_e": pose((20.0, 19.5, 0.0)),
        "bldg_1": pose((10.0, 3.5, 0.0)),
        "bldg_2": pose((30.0, 20.5, 0.0)),
        "lamp_1": pose((8.0, 8.2, 0.0)),
        "lamp_2": pose((20.0, 8.2, 0.0)),
        "lamp_3": pose((32.0, 15.8, 0.0)),
        "sign_1": pose((14.0, 7.5, 0.0)),
        "car_1": pose((22.0, 12.0, 0.0), yaw=1.5708),
        "kiosk_1": pose((6.0, 16.0, 0.0)),
        "bench_1": pose((16.0, 19.0, 0.0)),
    }
    return wrap(
        "01jfix01city000000000000000000",
        "City street, two building masses, streetlamps, a food-cart proxy.",
        "city",
        world,
        objects,
        layout,
        {"preset": "establishing_35", "look_at_id": "street_1"},
        {"location_m": [2.0, 12.0, 1.6], "look_at_m": [20.0, 12.0, 1.2], "focal_mm": 35.0},
        "night_urban",
    )


def zoo():
    world = {
        "extent_x_m": 36.0,
        "extent_y_m": 28.0,
        "height_m": 10.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "dirt",
        "terrain_amp_m": 0.0,
    }
    objects = [
        obj("path_1", "path", "slab", (28.0, 2.4, 0.08)),
        obj("enc_1", "enclosure", "enclosure", (8.0, 10.0, 3.5)),
        obj("enc_2", "enclosure", "enclosure", (8.0, 10.0, 3.5)),
        obj("hab_1", "habitat", "slab", (6.0, 7.0, 0.12)),
        obj("hab_2", "habitat", "slab", (6.0, 7.0, 0.12)),
        obj("lion_1", "animal", "mass", (2.2, 0.8, 1.2)),
        obj("bear_1", "animal", "mass", (2.4, 1.0, 1.4)),
        obj("bench_1", "bench", "seat", relations=[{"type": "along", "target": "path_1", "clearance_m": 0.4}]),
        obj("sign_1", "sign", "board"),
        obj("tree_1", "tree", "foliage"),
        obj("kiosk_1", "kiosk", "mass"),
        obj("lamp_1", "streetlamp", "pole"),
    ]
    layout = {
        "path_1": pose((18.0, 14.0, 0.0)),
        "enc_1": pose((8.0, 6.0, 0.0)),
        "enc_2": pose((28.0, 6.0, 0.0)),
        "hab_1": pose((8.0, 6.0, 0.0)),
        "hab_2": pose((28.0, 6.0, 0.0)),
        "lion_1": pose((8.0, 6.0, 0.0)),
        "bear_1": pose((28.0, 6.5, 0.0)),
        "bench_1": pose((18.0, 15.85, 0.0)),
        "sign_1": pose((12.0, 15.5, 0.0)),
        "tree_1": pose((18.0, 24.0, 0.0)),
        "kiosk_1": pose((4.0, 20.0, 0.0)),
        "lamp_1": pose((18.0, 12.2, 0.0)),
    }
    return wrap(
        "01jfix01zoo0000000000000000000",
        "Zoo: two enclosures, a path, a lion proxy, a sign.",
        "zoo",
        world,
        objects,
        layout,
        {"preset": "establishing_35", "look_at_id": "enc_1"},
        {"location_m": [18.0, 26.0, 1.7], "look_at_m": [18.0, 8.0, 0.8], "focal_mm": 35.0},
        "soft_day",
    )


def space():
    world = {
        "extent_x_m": 24.0,
        "extent_y_m": 18.0,
        "height_m": 8.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "metal_deck",
        "terrain_amp_m": 0.0,
    }
    objects = [
        obj("mod_1", "module", "module"),
        obj("mod_2", "module", "module", (3.0, 3.0, 2.5)),
        obj("crate_1", "crate", "mass"),
        obj("crate_2", "crate", "mass"),
        obj("crate_3", "crate", "mass"),
        obj("ant_1", "antenna", "pole"),
        obj("panel_1", "solar_panel", "slab", (4.0, 2.0, 0.08)),
        obj("tank_1", "tank", "proxy_cylinder"),
        obj("planet_1", "planet", "proxy_sphere", (16.0, 16.0, 16.0)),
    ]
    layout = {
        "mod_1": pose((6.0, 8.0, 0.0)),
        "mod_2": pose((16.0, 8.0, 0.0)),
        "crate_1": pose((10.0, 5.0, 0.0)),
        "crate_2": pose((11.4, 5.0, 0.0)),
        "crate_3": pose((10.7, 6.4, 0.0)),
        "ant_1": pose((20.0, 14.0, 0.0)),
        "panel_1": pose((12.0, 14.0, 0.0)),
        "tank_1": pose((4.0, 14.0, 0.0)),
        "planet_1": pose((12.0, 58.0, 8.0), snap=False),
    }
    return wrap(
        "01jfix01space00000000000000000",
        "Space station deck, crates, antenna, Earth in the HDRI.",
        "space",
        world,
        objects,
        layout,
        {"preset": "wide_24", "look_at_id": "mod_1"},
        {"location_m": [2.0, 1.5, 1.6], "look_at_m": [12.0, 9.0, 1.0], "focal_mm": 24.0},
        "stars",
    )


def beach():
    world = {
        "extent_x_m": 40.0,
        "extent_y_m": 28.0,
        "height_m": 10.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "sand",
        "terrain_amp_m": 0.05,
    }
    objects = [
        obj("rock_1", "rock", "mass"),
        obj("rock_2", "rock", "mass"),
        obj("rock_3", "rock", "mass"),
        obj("umb_1", "umbrella", "pole"),
        obj("umb_2", "umbrella", "pole"),
        obj("towel_1", "towel", "slab"),
        obj("towel_2", "towel", "slab"),
        obj("wood_1", "driftwood", "beam"),
        obj("bush_1", "bush", "foliage"),
        obj("board_1", "sign", "board"),
    ]
    layout = {
        "rock_1": pose((8.0, 22.0, 0.0)),
        "rock_2": pose((14.0, 24.0, 0.0)),
        "rock_3": pose((32.0, 21.0, 0.0)),
        "umb_1": pose((12.0, 10.0, 0.0)),
        "umb_2": pose((18.0, 9.0, 0.0)),
        "towel_1": pose((12.0, 11.5, 0.0)),
        "towel_2": pose((18.0, 10.5, 0.0)),
        "wood_1": pose((26.0, 16.0, 0.0), yaw=0.6),
        "bush_1": pose((6.0, 6.0, 0.0)),
        "board_1": pose((4.0, 8.0, 0.0)),
    }
    return wrap(
        "01jfix01beach00000000000000000",
        "Beach, rocks, umbrellas, driftwood, sunset.",
        "beach",
        world,
        objects,
        layout,
        {"preset": "establishing_35", "look_at_id": "umb_1"},
        {"location_m": [4.0, 4.0, 1.6], "look_at_m": [18.0, 14.0, 0.5], "focal_mm": 35.0},
        "sunset",
    )


def generic():
    world = {
        "extent_x_m": 20.0,
        "extent_y_m": 20.0,
        "height_m": 8.0,
        "wall_thickness_m": 0.15,
        "openings": [],
        "ground": "floor",
        "terrain_amp_m": 0.0,
    }
    objects = [
        obj("mass_1", "prop_a", "mass"),
        obj("mass_2", "prop_b", "mass"),
        obj("pole_1", "pole", "pole"),
        obj("slab_1", "platform", "slab", (4.0, 4.0, 0.15)),
    ]
    layout = {
        "mass_1": pose((6.0, 8.0, 0.0)),
        "mass_2": pose((14.0, 8.0, 0.0)),
        "pole_1": pose((10.0, 14.0, 0.0)),
        "slab_1": pose((10.0, 8.0, 0.0)),
    }
    return wrap(
        "01jfix01generic000000000000000",
        "Generic ground with a few blocks.",
        "generic",
        world,
        objects,
        layout,
        {"preset": "medium_50", "look_at_id": "slab_1"},
        {"location_m": [2.0, 2.0, 1.6], "look_at_m": [10.0, 8.0, 0.5], "focal_mm": 50.0},
        "high_key",
    )


FIXTURES = {
    "living_room_v0.json": living_room,
    "park_v0.json": park,
    "forest_v0.json": forest,
    "city_v0.json": city,
    "zoo_v0.json": zoo,
    "space_v0.json": space,
    "beach_v0.json": beach,
    "generic_v0.json": generic,
}

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


def main() -> None:
    ADDON_FIXTURES.mkdir(parents=True, exist_ok=True)
    BACKEND_FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, fn in FIXTURES.items():
        doc = fn()
        text = json.dumps(doc, indent=2)
        (BACKEND_FIXTURES / name).write_text(text, encoding="utf-8")
        (ADDON_FIXTURES / name).write_text(text, encoding="utf-8")
        print("wrote", name, "objects", len(doc["objects"]))
    index = {"domain_files": DOMAIN_FILES}
    (BACKEND_FIXTURES / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    (ADDON_FIXTURES / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
