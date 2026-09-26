from ..mesh_util import GROUND_RGB, make_box
from ..terrain import build_ground


def build_shell(world: dict, collection, job_id: str) -> None:
    x = float(world["extent_x_m"])
    y = float(world["extent_y_m"])
    amp = float(world.get("terrain_amp_m") or 0.7)
    props = {"aidir.role": "shell", "aidir.job_id": job_id, "aidir.domain": "beach"}
    build_ground(
        f"aidir.{job_id}.sand",
        x,
        y,
        collection,
        props,
        "sand",
        amp,
        path_half=0.0,
        seed=job_id,
    )
    water_y = y * 0.28
    cy = y - water_y / 2.0
    make_box(
        f"aidir.{job_id}.water",
        x,
        water_y,
        0.05,
        (x / 2.0, cy, -0.02),
        collection,
        props,
        (0.10, 0.28, 0.42, 1.0),
    )
