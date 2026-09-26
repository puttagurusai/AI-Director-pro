"""Geometry Nodes scatter when we need cover PH does not instance for us (grass/undergrowth)."""

from __future__ import annotations

import bpy

from .logutil import log


def _make_group(name: str, density: float, scale: float, seed: int, collection):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    iface = ng.interface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = ng.nodes, ng.links
    n_in = nodes.new("NodeGroupInput")
    n_out = nodes.new("NodeGroupOutput")
    dist = nodes.new("GeometryNodeDistributePointsOnFaces")
    if "Density" in dist.inputs:
        dist.inputs["Density"].default_value = density
    if "Seed" in dist.inputs:
        dist.inputs["Seed"].default_value = seed
    inst = nodes.new("GeometryNodeInstanceOnPoints")
    info = nodes.new("GeometryNodeCollectionInfo")
    if "Collection" in info.inputs:
        info.inputs["Collection"].default_value = collection
    for sock_name in ("Separate Children", "Reset Children"):
        if sock_name in info.inputs:
            info.inputs[sock_name].default_value = True
    rot = nodes.new("FunctionNodeRandomValue")
    try:
        rot.data_type = "FLOAT_VECTOR"
    except Exception:
        pass
    if "Min" in rot.inputs:
        try:
            rot.inputs["Min"].default_value = (0.0, 0.0, 0.0)
            rot.inputs["Max"].default_value = (0.0, 0.0, 6.28)
        except Exception:
            pass
    if "Seed" in rot.inputs:
        rot.inputs["Seed"].default_value = seed + 3
    join = nodes.new("GeometryNodeJoinGeometry")
    scale_n = nodes.new("GeometryNodeScaleElements") if False else None
    links.new(n_in.outputs[0], dist.inputs[0])
    links.new(dist.outputs[0], inst.inputs["Points"])
    links.new(info.outputs[0], inst.inputs["Instance"])
    if "Rotation" in inst.inputs and rot.outputs:
        try:
            links.new(rot.outputs[0], inst.inputs["Rotation"])
        except Exception:
            pass
    if "Scale" in inst.inputs:
        try:
            inst.inputs["Scale"].default_value = (scale, scale, scale)
        except Exception:
            pass
    try:
        links.new(n_in.outputs[0], join.inputs[0])
        links.new(inst.outputs[0], join.inputs[0])
        links.new(join.outputs[0], n_out.inputs[0])
    except Exception:
        links.new(inst.outputs[0], n_out.inputs[0])
    n_in.location = (-400, 0)
    dist.location = (-150, 80)
    info.location = (-150, -160)
    inst.location = (120, 0)
    join.location = (340, 0)
    n_out.location = (540, 0)
    return ng


def scatter_on_ground(ground, instance_objects, job_id: str, density: float = 0.35) -> None:
    if ground is None or ground.type != "MESH" or not instance_objects:
        return
    name = f"AIDIR_scatter_src.{job_id[:8]}"
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    for obj in instance_objects[:8]:
        if obj.name not in col.objects:
            try:
                col.objects.link(obj)
            except Exception:
                pass
    try:
        ng = _make_group(f"AIDIR_GN_scatter_{job_id[:8]}", density, 0.55, abs(hash(job_id)) % 10000, col)
        mod = ground.modifiers.new("AIDIR_scatter", "NODES")
        mod.node_group = ng
        log(f"gn scatter on {ground.name} n={len(instance_objects)} dens={density}")
    except Exception as exc:
        log(f"gn scatter skip: {exc}")
