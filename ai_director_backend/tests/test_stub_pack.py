from app.ir.schema import SceneObjectDraft, WorldSpec
from app.layout.stub_pack import stub_pack_grid


def test_stub_pack_covers_ids():
    world = WorldSpec(extent_x_m=20, extent_y_m=20, height_m=8)
    objs = [
        SceneObjectDraft(id="a", category="sofa", part="seat"),
        SceneObjectDraft(id="b", category="tree", part="foliage"),
        SceneObjectDraft(id="c", category="crate", part="mass"),
    ]
    poses = stub_pack_grid(objs, world)
    assert set(poses) == {"a", "b", "c"}
    for p in poses.values():
        x, y, _ = p.location_m
        assert 0 <= x <= 20
        assert 0 <= y <= 20
