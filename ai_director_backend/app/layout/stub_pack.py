from __future__ import annotations

import math

from app.ir.schema import Pose, SceneObjectDraft, WorldSpec, default_size


def stub_pack_grid(objects: list[SceneObjectDraft], world: WorldSpec) -> dict[str, Pose]:
    """Spread across most of the ground, not a 2m cluster in the corner."""
    wx, wy = float(world.extent_x_m), float(world.extent_y_m)
    n = max(1, len(objects))
    cols = max(2, int(math.ceil(math.sqrt(n))))
    rows = max(1, int(math.ceil(n / cols)))
    margin_x = wx * 0.12
    margin_y = wy * 0.12
    usable_x = max(2.0, wx - 2 * margin_x)
    usable_y = max(2.0, wy - 2 * margin_y)
    cell_x = usable_x / cols
    cell_y = usable_y / rows
    poses: dict[str, Pose] = {}
    for i, obj in enumerate(objects):
        sx, sy, sz = default_size(obj.category, obj.part)
        c, r = i % cols, i // cols
        x = margin_x + (c + 0.5) * cell_x
        y = margin_y + (r + 0.5) * cell_y
        # keep footprint inside
        x = min(max(x, sx / 2 + 0.2), wx - sx / 2 - 0.2)
        y = min(max(y, sy / 2 + 0.2), wy - sy / 2 - 0.2)
        z = 0.0
        yaw = 0.0
        if obj.category in ("art_frame", "mirror"):
            z = 1.4
        if obj.category == "path":
            x, y = wx / 2.0, wy / 2.0
        if obj.category == "planet":
            x, y, z = wx / 2.0, wy + 40.0, 8.0
        poses[obj.id] = Pose(
            location_m=(round(x, 3), round(y, 3), z),
            rotation_euler_rad=(0.0, 0.0, yaw),
            support="ground",
            snap_z_pending=obj.category not in ("art_frame", "mirror", "planet"),
        )
    return poses
