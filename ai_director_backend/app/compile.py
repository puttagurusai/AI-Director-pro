from __future__ import annotations

import os
import uuid

from app.catalog.polyhaven import pick_hdri, search_model
from app.ir.schema import (
    Attribution,
    CameraPose,
    Fallback,
    HdriRef,
    LightSpec,
    PlannerDraft,
    Pose,
    SceneIR,
    SceneObject,
    default_size,
)
from app.layout.stub_pack import stub_pack_grid

LIGHTS = {
    "warm_interior": [
        LightSpec(role="key", type="AREA", energy=250, color_temp_k=3500, offset_from_camera_m=(1.2, 0.4, 0.8)),
        LightSpec(role="fill", type="AREA", energy=80, color_temp_k=4500, offset_from_camera_m=(-1.5, 0.2, 0.4)),
        LightSpec(role="rim", type="AREA", energy=40, color_temp_k=5000, offset_from_camera_m=(0.0, 0.3, 1.2)),
    ],
    "stars": [
        LightSpec(role="sun", type="SUN", energy=2, color_temp_k=7000, offset_from_camera_m=(0.0, 2.0, 4.0)),
        LightSpec(role="fill", type="AREA", energy=20, color_temp_k=8000, offset_from_camera_m=(-1.0, 0.4, 0.5)),
    ],
    "sunset": [
        LightSpec(role="sun", type="SUN", energy=8, color_temp_k=3200, offset_from_camera_m=(2.0, 1.0, 3.0)),
        LightSpec(role="fill", type="AREA", energy=40, color_temp_k=5000, offset_from_camera_m=(-1.2, 0.2, 0.6)),
    ],
    "night_urban": [
        LightSpec(role="key", type="AREA", energy=180, color_temp_k=4000, offset_from_camera_m=(1.0, 0.8, 1.0)),
        LightSpec(role="fill", type="AREA", energy=30, color_temp_k=6500, offset_from_camera_m=(-1.4, 0.2, 0.4)),
    ],
}


def _camera(draft: PlannerDraft, poses: dict[str, Pose]) -> CameraPose:
    pts = [p.location_m for p in poses.values() if p.location_m[1] < draft.world.extent_y_m + 5]
    if not pts:
        pts = [(draft.world.extent_x_m / 2.0, draft.world.extent_y_m / 2.0, 0.0)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    span = max(max(xs) - min(xs), max(ys) - min(ys), 6.0)
    dist = span * 1.35
    loc = (cx - dist * 0.55, cy - dist * 0.75, max(4.0, span * 0.55))
    look_at = (cx, cy, 0.6)
    focal = 24.0 if draft.domain != "interior" else 35.0
    return CameraPose(location_m=loc, look_at_m=look_at, focal_mm=focal)


def compile_scene(draft: PlannerDraft, prompt: str, api_base: str = "http://127.0.0.1:8000") -> SceneIR:
    job_id = uuid.uuid4().hex
    poses = stub_pack_grid(draft.objects, draft.world)
    objects: list[SceneObject] = []
    fallbacks: list[Fallback] = []
    attrib: list[Attribution] = []
    warnings: list[str] = ["Powered by Poly Haven"]
    for spec in draft.objects:
        size = default_size(spec.category, spec.part)
        catalog_id = None
        license_ = None
        asset_url = None
        hit = None
        use_ph = os.environ.get("AIDIR_SKIP_PH") != "1"
        already = sum(1 for o in objects if o.catalog_id)
        if use_ph and already < 8:
            hit = search_model(spec.category)
        if hit and hit.get("url"):
            cid = hit["catalog_id"]
            catalog_id = cid
            license_ = "CC0"
            asset_url = str(hit["url"])
            if hit.get("real_size_m"):
                size = tuple(float(x) for x in hit["real_size_m"])
            attrib.append(Attribution(catalog_id=cid, license="CC0", text=hit["attribution"]))
        if not catalog_id:
            fallbacks.append(Fallback(object_id=spec.id, reason="no_catalog_hit", primitive=spec.part))
        objects.append(
            SceneObject(
                id=spec.id,
                category=spec.category,
                part=spec.part,
                relations=spec.relations,
                style_tags=spec.style_tags,
                catalog_id=catalog_id,
                license=license_,
                real_size_m=size,
                asset_url=asset_url,
            )
        )
    hdri = None
    try:
        h = None
        if os.environ.get("AIDIR_SKIP_PH") != "1":
            h = pick_hdri(draft.light_preset, draft.domain)
        if h and h.get("url"):
            hdri = HdriRef(
                catalog_id=h["catalog_id"],
                intensity=1.0,
                rotation_z=0.0,
                asset_url=str(h["url"]),
            )
            attrib.append(Attribution(catalog_id=h["catalog_id"], license="CC0", text=h["attribution"]))
    except Exception as exc:
        warnings.append(f"hdri_fail:{exc}")
    lights = LIGHTS.get(draft.light_preset) or LIGHTS["warm_interior"]
    return SceneIR(
        schema_version="0.1",
        job_id=job_id,
        prompt=prompt,
        domain=draft.domain,
        world=draft.world,
        objects=objects,
        layout=poses,
        camera=draft.camera,
        camera_pose=_camera(draft, poses),
        lights=list(lights),
        hdri=hdri,
        light_preset=draft.light_preset,
        fallbacks=fallbacks,
        warnings=warnings,
        attribution=attrib,
        status="ready",
    )
