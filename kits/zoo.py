from ..terrain import build_ground


def build_shell(world: dict, collection, job_id: str) -> None:
    x = float(world["extent_x_m"])
    y = float(world["extent_y_m"])
    amp = float(world.get("terrain_amp_m") or 0.85)
    props = {"aidir.role": "shell", "aidir.job_id": job_id, "aidir.domain": "zoo"}
    build_ground(
        f"aidir.{job_id}.ground",
        x,
        y,
        collection,
        props,
        world.get("ground") or "dirt",
        amp,
        path_half=max(2.0, x * 0.055),
        seed=job_id,
    )
