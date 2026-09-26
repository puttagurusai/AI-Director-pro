from ..terrain import build_ground


def build_shell(world: dict, collection, job_id: str) -> None:
    x = float(world["extent_x_m"])
    y = float(world["extent_y_m"])
    props = {"aidir.role": "shell", "aidir.job_id": job_id, "aidir.domain": "city"}
    build_ground(
        f"aidir.{job_id}.ground",
        x,
        y,
        collection,
        props,
        "pavement",
        amp=0.12,
        path_half=max(3.5, x * 0.12),
        seed=job_id,
    )
