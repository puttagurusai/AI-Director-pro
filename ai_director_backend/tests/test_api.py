from fastapi.testclient import TestClient

from app.main import app
from app.planner.domain import infer_domain, resolve_domain


def test_infer_domain():
    assert infer_domain("a park at dusk") == "park"
    assert infer_domain("space station deck") == "space"
    assert infer_domain("city street downtown") == "city"
    assert resolve_domain("zoo", "a park") == "zoo"
    assert resolve_domain("auto", "forest clearing") == "forest"


def test_health_and_scene():
    client = TestClient(app)
    assert client.get("/healthz").json()["ok"] is True
    r = client.post("/v1/scenes", json={"prompt": "zoo with a lion", "domain": "auto"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    ir = client.get(f"/v1/scenes/{job_id}").json()
    assert ir["domain"] == "zoo"
    assert set(ir["layout"]) == {o["id"] for o in ir["objects"]}
    assert any(o["category"] == "animal" for o in ir["objects"])
    xs = [p["location_m"][0] for p in ir["layout"].values()]
    assert max(xs) - min(xs) > 8.0
