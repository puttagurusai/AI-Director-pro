from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADDON))

from app.ir.schema import SceneIR  # noqa: E402
from ir import IRError, validate_scene_ir  # noqa: E402

FIXTURE_DIR = ROOT / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    [
        "living_room_v0.json",
        "park_v0.json",
        "forest_v0.json",
        "city_v0.json",
        "zoo_v0.json",
        "space_v0.json",
        "beach_v0.json",
        "generic_v0.json",
    ],
)
def test_pydantic_and_stdlib_accept_fixtures(name: str):
    doc = _load(name)
    SceneIR.model_validate(doc)
    validate_scene_ir(doc)


def test_extra_field_rejected():
    doc = deepcopy(_load("living_room_v0.json"))
    doc["objects"][0]["bpy"] = "import os"
    with pytest.raises((IRError, Exception)):
        validate_scene_ir(doc)
    with pytest.raises(Exception):
        SceneIR.model_validate(doc)


def test_missing_layout_key_rejected():
    doc = deepcopy(_load("living_room_v0.json"))
    doc["layout"].pop("sofa_1")
    with pytest.raises(IRError):
        validate_scene_ir(doc)
    with pytest.raises(Exception):
        SceneIR.model_validate(doc)


def _aabb(center, size, yaw=0.0):
    hx, hy = size[0] / 2.0, size[1] / 2.0
    if abs(abs(yaw) - 1.5708) < 0.05:
        hx, hy = size[1] / 2.0, size[0] / 2.0
    x, y = center[0], center[1]
    return x - hx, y - hy, x + hx, y + hy


def test_living_room_core_predicates():
    doc = _load("living_room_v0.json")
    by = {o["id"]: o for o in doc["objects"]}
    sofa = doc["layout"]["sofa_1"]["location_m"]
    table = doc["layout"]["table_1"]["location_m"]
    plant = doc["layout"]["plant_1"]["location_m"]
    sofa_sz = by["sofa_1"]["real_size_m"]
    table_sz = by["table_1"]["real_size_m"]
    plant_sz = by["plant_1"]["real_size_m"]
    sofa_aabb = _aabb(sofa, sofa_sz)
    table_aabb = _aabb(table, table_sz)
    plant_aabb = _aabb(plant, plant_sz)
    assert abs(sofa[1] - (0.08 + sofa_sz[1] / 2)) < 0.02
    gap_y = table_aabb[1] - sofa_aabb[3]
    assert gap_y >= 0.40
    gap_x = plant_aabb[0] - sofa_aabb[2]
    assert 0.15 <= gap_x <= 0.60
    rug = doc["layout"]["rug_1"]["location_m"]
    assert abs(rug[0] - 2.75) < 0.02
    assert abs(rug[1] - 2.10) < 0.02
    cam = doc["camera_pose"]["location_m"]
    assert 0.0 <= cam[0] <= 5.5
    assert 0.0 <= cam[1] <= 4.2


def test_park_objects_inside_ground():
    doc = _load("park_v0.json")
    wx, wy = doc["world"]["extent_x_m"], doc["world"]["extent_y_m"]
    for oid, pose in doc["layout"].items():
        x, y, _ = pose["location_m"]
        assert 0.0 <= x <= wx
        assert 0.0 <= y <= wy, oid
    path = doc["layout"]["path_1"]["location_m"]
    b1 = doc["layout"]["bench_1"]["location_m"]
    assert abs(b1[1] - path[1]) < 2.5
