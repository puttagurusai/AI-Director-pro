from ..terrain import build_ground


def build_shell(world: dict, collection, job_id: str) -> None:
    x = float(world["extent_x_m"])
    y = float(world["extent_y_m"])
    amp = float(world.get("terrain_amp_m") or 1.8)
    props = {"aidir.role": "shell", "aidir.job_id": job_id, "aidir.domain": "forest"}
    build_ground(
        f"aidir.{job_id}.ground",
        x,
        y,
        collection,
        props,
        world.get("ground") or "dirt",
        amp,
        path_half=0.0,
        seed=job_id,
    )
