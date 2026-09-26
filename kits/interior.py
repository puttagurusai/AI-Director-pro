"""Interior box_room: floor, ceiling, segment walls with door/window gaps."""

from __future__ import annotations

from ..mesh_util import GROUND_RGB, make_box


def _wall_segments(wall, extent_x, extent_y, height, thick, openings):
    """Return list of (cx, cy, sx, sy) boxes in inner-SW coords, thickness outward."""
    wall_ops = [o for o in openings if o.get("wall") == wall]
    if wall in ("wall.south", "wall.north"):
        length = extent_x
        y = -thick / 2.0 if wall == "wall.south" else extent_y + thick / 2.0
        cuts = []
        for o in wall_ops:
            a = max(0.0, float(o["offset_m"]))
            b = min(length, a + float(o["width_m"]))
            cuts.append((a, b))
        cuts.sort()
        merged = []
        for a, b in cuts:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        x0 = 0.0
        segs = []
        for a, b in merged:
            if a - x0 > 0.02:
                w = a - x0
                segs.append((x0 + w / 2.0, y, w, thick))
            x0 = b
        if length - x0 > 0.02:
            w = length - x0
            segs.append((x0 + w / 2.0, y, w, thick))
        if not segs:
            segs.append((length / 2.0, y, length, thick))
        return segs
    length = extent_y
    x = -thick / 2.0 if wall == "wall.west" else extent_x + thick / 2.0
    cuts = []
    for o in openings:
        if o.get("wall") != wall:
            continue
        a = max(0.0, float(o["offset_m"]))
        b = min(length, a + float(o["width_m"]))
        cuts.append((a, b))
    cuts.sort()
    merged = []
    for a, b in cuts:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    y0 = 0.0
    segs = []
    for a, b in merged:
        if a - y0 > 0.02:
            d = a - y0
            segs.append((x, y0 + d / 2.0, thick, d))
        y0 = b
    if length - y0 > 0.02:
        d = length - y0
        segs.append((x, y0 + d / 2.0, thick, d))
    if not segs:
        segs.append((x, length / 2.0, thick, length))
    return segs


def build_shell(world: dict, collection, job_id: str) -> None:
    x = float(world["extent_x_m"])
    y = float(world["extent_y_m"])
    h = float(world["height_m"])
    t = float(world.get("wall_thickness_m") or 0.15)
    openings = world.get("openings") or []
    props = {"aidir.role": "shell", "aidir.job_id": job_id, "aidir.domain": "interior"}
    make_box(
        f"aidir.{job_id}.floor",
        x,
        y,
        0.04,
        (x / 2.0, y / 2.0, -0.04),
        collection,
        props,
        GROUND_RGB["floor"],
        origin_ground=True,
    )
    make_box(
        f"aidir.{job_id}.ceiling",
        x,
        y,
        0.04,
        (x / 2.0, y / 2.0, h),
        collection,
        props,
        (0.55, 0.55, 0.52, 1.0),
        origin_ground=True,
    )
    wall_rgba = (0.62, 0.60, 0.56, 1.0)
    for wall in ("wall.south", "wall.north", "wall.west", "wall.east"):
        for i, (cx, cy, sx, sy) in enumerate(_wall_segments(wall, x, y, h, t, openings)):
            make_box(
                f"aidir.{job_id}.{wall}.{i}",
                sx,
                sy,
                h,
                (cx, cy, 0.0),
                collection,
                props,
                wall_rgba,
                origin_ground=True,
            )
