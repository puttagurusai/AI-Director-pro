"""SceneIR v0.1 and PlannerDraft — server-side Pydantic models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "0.1"

Domain = Literal[
    "interior", "park", "forest", "city", "zoo", "space", "beach", "generic"
]
UiDomain = Literal["auto", Domain]

Part = Literal[
    "slab",
    "beam",
    "cover",
    "mass",
    "pole",
    "board",
    "seat",
    "puddle",
    "foliage",
    "enclosure",
    "module",
    "proxy_box",
    "proxy_cylinder",
    "proxy_sphere",
]

RelationType = Literal[
    "on",
    "next_to",
    "facing",
    "against_wall",
    "in_front_of",
    "behind",
    "centered_on",
    "along",
    "scatter",
]

WallId = Literal["wall.north", "wall.south", "wall.east", "wall.west"]
GroundKind = Literal[
    "floor", "grass", "dirt", "pavement", "sand", "water_edge", "metal_deck", "void"
]
LightPreset = Literal[
    "high_key",
    "soft_day",
    "warm_interior",
    "noir",
    "overcast",
    "sunset",
    "night_urban",
    "stars",
]
ID_PATTERN = r"^[a-z][a-z0-9_]{0,31}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Relation(Strict):
    type: RelationType
    target: str
    clearance_m: float = 0.15


class Opening(Strict):
    type: Literal["door", "window"]
    wall: WallId
    offset_m: float
    width_m: float
    sill_m: float = 0.0
    height_m: float


class WorldSpec(Strict):
    extent_x_m: float = Field(ge=4.0, le=250.0)
    extent_y_m: float = Field(ge=4.0, le=250.0)
    height_m: float = Field(ge=2.0, le=40.0)
    wall_thickness_m: float = 0.15
    openings: list[Opening] = Field(default_factory=list)
    ground: GroundKind = "floor"
    terrain_amp_m: float = Field(default=0.0, ge=0.0, le=3.0)


class SceneObjectDraft(Strict):
    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    part: Part = "mass"
    relations: list[Relation] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)


class CameraDraft(Strict):
    preset: Literal["establishing_35", "medium_50", "wide_24"] = "establishing_35"
    look_at_id: Optional[str] = None


class CameraPose(Strict):
    location_m: tuple[float, float, float]
    look_at_m: tuple[float, float, float]
    focal_mm: float = 35.0


class PlannerDraft(Strict):
    schema_version: Literal["0.1"] = "0.1"
    domain: Domain
    world: WorldSpec
    objects: list[SceneObjectDraft]
    camera: CameraDraft
    light_preset: LightPreset
    notes: str = ""


class Pose(Strict):
    location_m: tuple[float, float, float]
    rotation_euler_rad: tuple[float, float, float]
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    support: str = "ground"
    snap_z_pending: bool = True
    infeasibility: Optional[str] = None


class LightSpec(Strict):
    role: Literal["key", "fill", "rim", "sun"]
    type: Literal["AREA", "SUN"]
    energy: float
    color_temp_k: int
    offset_from_camera_m: tuple[float, float, float]


class HdriRef(Strict):
    catalog_id: str
    intensity: float = 1.0
    rotation_z: float = 0.0
    asset_url: Optional[str] = None


class Fallback(Strict):
    object_id: str
    reason: Literal[
        "no_catalog_hit",
        "scale_clamped",
        "relation_dropped",
        "out_of_ground",
        "wall_on_outdoor",
    ]
    primitive: Part


class Attribution(Strict):
    catalog_id: str
    license: Literal["CC0"]
    text: str


class SceneObject(SceneObjectDraft):
    catalog_id: Optional[str] = None
    license: Optional[Literal["CC0"]] = None
    real_size_m: tuple[float, float, float]
    asset_url: Optional[str] = None


class SceneIR(Strict):
    schema_version: Literal["0.1"] = "0.1"
    job_id: str
    prompt: str
    domain: Domain
    world: WorldSpec
    objects: list[SceneObject]
    layout: dict[str, Pose]
    camera: CameraDraft
    camera_pose: CameraPose
    lights: list[LightSpec]
    hdri: Optional[HdriRef] = None
    light_preset: LightPreset
    fallbacks: list[Fallback] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    attribution: list[Attribution] = Field(default_factory=list)
    status: Literal[
        "queued", "planning", "solving", "ready", "applying", "complete", "failed"
    ]

    @model_validator(mode="after")
    def layout_covers_objects(self) -> "SceneIR":
        ids = {o.id for o in self.objects}
        keys = set(self.layout)
        if ids != keys:
            missing = ids - keys
            extra = keys - ids
            raise ValueError(f"layout keys must equal object ids; missing={missing} extra={extra}")
        return self


DEFAULT_EXTENTS: dict[str, tuple[float, float, float]] = {
    "sofa": (2.10, 0.90, 0.85),
    "armchair": (0.85, 0.85, 0.90),
    "dining_chair": (0.50, 0.55, 0.95),
    "stool": (0.40, 0.40, 0.45),
    "ottoman": (0.80, 0.60, 0.40),
    "coffee_table": (1.20, 0.60, 0.40),
    "dining_table": (1.80, 0.90, 0.75),
    "desk": (1.40, 0.70, 0.75),
    "nightstand": (0.50, 0.40, 0.55),
    "side_table": (0.45, 0.45, 0.55),
    "bed": (2.00, 1.60, 0.50),
    "bookshelf": (0.80, 0.30, 1.80),
    "cabinet": (1.20, 0.45, 0.85),
    "dresser": (1.20, 0.50, 0.80),
    "lamp_floor": (0.30, 0.30, 1.50),
    "plant": (0.45, 0.45, 1.20),
    "rug": (2.40, 1.60, 0.02),
    "art_frame": (0.70, 0.04, 0.90),
    "mirror": (0.50, 0.04, 0.75),
    "tree": (2.00, 2.00, 6.00),
    "bush": (1.20, 1.20, 1.40),
    "bench": (1.60, 0.50, 0.90),
    "path": (12.00, 2.40, 0.08),
    "rock": (1.50, 1.20, 0.80),
    "log": (2.00, 0.40, 0.40),
    "streetlamp": (0.20, 0.20, 4.50),
    "sign": (0.80, 0.08, 1.80),
    "fountain": (2.00, 2.00, 1.20),
    "pond": (6.00, 4.00, 0.05),
    "building_mass": (8.00, 8.00, 12.00),
    "sidewalk": (12.00, 2.00, 0.08),
    "vehicle": (4.20, 1.80, 1.50),
    "fence": (6.00, 0.10, 1.40),
    "enclosure": (6.00, 8.00, 3.50),
    "habitat": (5.00, 6.00, 0.15),
    "animal": (2.20, 0.80, 1.20),
    "kiosk": (2.00, 2.00, 2.40),
    "crate": (1.20, 1.20, 1.20),
    "antenna": (0.30, 0.30, 6.00),
    "solar_panel": (3.00, 1.50, 0.10),
    "planet": (20.0, 20.0, 20.0),
    "module": (4.00, 4.00, 3.00),
    "tank": (1.50, 1.50, 2.00),
    "umbrella": (1.80, 1.80, 2.20),
    "towel": (1.80, 0.80, 0.04),
    "driftwood": (2.00, 0.40, 0.30),
}


def default_size(category: str, part: str) -> tuple[float, float, float]:
    if category in DEFAULT_EXTENTS:
        return DEFAULT_EXTENTS[category]
    fallback = {
        "slab": (4.0, 2.0, 0.08),
        "beam": (3.0, 0.12, 0.12),
        "cover": (4.0, 4.0, 2.8),
        "mass": (1.0, 1.0, 1.0),
        "pole": (0.15, 0.15, 3.0),
        "board": (1.2, 0.06, 0.8),
        "seat": (1.6, 0.5, 0.9),
        "puddle": (3.0, 2.0, 0.04),
        "foliage": (2.0, 2.0, 5.0),
        "enclosure": (6.0, 8.0, 3.5),
        "module": (4.0, 4.0, 3.0),
        "proxy_box": (1.0, 1.0, 1.0),
        "proxy_cylinder": (0.6, 0.6, 1.2),
        "proxy_sphere": (1.0, 1.0, 1.0),
    }
    return fallback.get(part, (1.0, 1.0, 1.0))
