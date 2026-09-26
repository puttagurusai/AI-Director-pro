from ..mesh_util import GROUND_RGB, make_box


def build_shell(world: dict, collection, job_id: str) -> None:
    x = float(world["extent_x_m"])
    y = float(world["extent_y_m"])
    ground = world.get("ground") or "floor"
    props = {"aidir.role": "shell", "aidir.job_id": job_id, "aidir.domain": "generic"}
    make_box(
        f"aidir.{job_id}.ground",
        x,
        y,
        0.06,
        (x / 2.0, y / 2.0, -0.06),
        collection,
        props,
        GROUND_RGB.get(ground, GROUND_RGB["floor"]),
    )
