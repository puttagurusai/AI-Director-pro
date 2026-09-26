"""Deterministic SceneIR apply. bmesh / bpy.data only."""

from __future__ import annotations

import bpy
from mathutils import Vector

from . import mesh_util
from .kits import KITS
from .layout import FOOT
from .logutil import log
from .lookdev import apply_look


def job_collection_name(job_id: str) -> str:
    return f"AIDirector.{job_id}"


def wipe_job(job_id: str) -> None:
    for col in list(bpy.data.collections):
        if col.name.startswith("AIDirector."):
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(col)
    for obj in list(bpy.data.objects):
        if obj.get("aidir.job_id") or obj.name.startswith("aidir."):
            bpy.data.objects.remove(obj, do_unlink=True)


def _ensure_collection(job_id: str):
    name = job_collection_name(job_id)
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def _base_props(ir, oid, obj_spec):
    return {
        "aidir.object_id": oid,
        "aidir.job_id": ir["job_id"],
        "aidir.domain": ir["domain"],
        "aidir.part": obj_spec.get("part") or "mass",
        "aidir.category": obj_spec.get("category") or "",
        "aidir.role": "prop",
    }


def spawn_part(ir, obj_spec, pose, collection):
    oid = obj_spec["id"]
    if obj_spec.get("cache_path"):
        empty = bpy.data.objects.new(f"aidir.{oid}", None)
        empty.location = pose["location_m"]
        empty.rotation_euler[2] = pose["rotation_euler_rad"][2]
        for k, v in _base_props(ir, oid, obj_spec).items():
            empty[k] = v
        collection.objects.link(empty)
        return empty
    part = obj_spec.get("part") or "mass"
    sx, sy, sz = obj_spec["real_size_m"]
    loc = pose["location_m"]
    yaw = pose["rotation_euler_rad"][2]
    props = _base_props(ir, oid, obj_spec)
    rgba = mesh_util.PART_RGB.get(part)
    name = f"aidir.{oid}"
    if part == "foliage":
        trunk_h = max(0.4, sz * 0.25)
        mesh_util.make_box(
            name + ".trunk",
            min(sx, sy) * 0.18,
            min(sx, sy) * 0.18,
            trunk_h,
            (loc[0], loc[1], loc[2]),
            collection,
            props,
            (0.28, 0.18, 0.10, 1.0),
        )
        obj = mesh_util.make_cone(
            name,
            max(sx, sy) * 0.45,
            sz * 0.75,
            (loc[0], loc[1], loc[2] + trunk_h * 0.7),
            collection,
            props,
            mesh_util.PART_RGB["foliage"],
        )
    elif part == "proxy_sphere":
        obj = mesh_util.make_icosphere(name, max(sx, sy, sz) * 0.5, tuple(loc), collection, props, rgba)
    elif part == "seat":
        obj = mesh_util.make_box(name, sx, sy, max(0.08, sz * 0.18), tuple(loc), collection, props, rgba)
        mesh_util.make_box(
            name + ".back",
            sx,
            max(0.08, sy * 0.18),
            sz * 0.45,
            (loc[0], loc[1] - sy * 0.35, loc[2] + sz * 0.18),
            collection,
            props,
            rgba,
        )
    elif part == "enclosure":
        obj = mesh_util.make_box(name + ".roof", sx, sy, 0.12, (loc[0], loc[1], loc[2] + sz * 0.85), collection, props, rgba)
        for dx, dy in ((-sx * 0.45, -sy * 0.45), (sx * 0.45, -sy * 0.45), (-sx * 0.45, sy * 0.45), (sx * 0.45, sy * 0.45)):
            mesh_util.make_box(
                f"{name}.p{dx:.0f}{dy:.0f}",
                0.12,
                0.12,
                sz,
                (loc[0] + dx, loc[1] + dy, loc[2]),
                collection,
                props,
                (0.3, 0.3, 0.28, 1.0),
            )
    elif part in ("proxy_cylinder", "pole", "tank"):
        obj = mesh_util.make_box(name, min(sx, 0.4) if part == "pole" else sx, min(sy, 0.4) if part == "pole" else sy, sz, tuple(loc), collection, props, rgba)
    else:
        obj = mesh_util.make_box(name, sx, sy, sz, tuple(loc), collection, props, rgba)
    obj.rotation_euler[2] = yaw
    return obj


def _place_camera(ir, collection):
    pose = ir["camera_pose"]
    cam_data = bpy.data.cameras.new(f"aidir.{ir['job_id']}.cam")
    cam_data.lens = float(pose.get("focal_mm") or 35.0)
    cam = bpy.data.objects.new(f"aidir.{ir['job_id']}.camera", cam_data)
    cam.location = pose["location_m"]
    cam["aidir.job_id"] = ir["job_id"]
    cam["aidir.role"] = "camera"
    collection.objects.link(cam)
    mesh_util.look_at(cam, pose["look_at_m"])
    bpy.context.scene.camera = cam
    return cam


def _place_lights(ir, cam, collection):
    mw = cam.matrix_world
    for i, spec in enumerate(ir.get("lights") or []):
        ltype = spec.get("type") or "AREA"
        data = bpy.data.lights.new(f"aidir.{ir['job_id']}.L{i}", ltype)
        data.energy = float(spec.get("energy") or 100.0)
        rgb = mesh_util.kelvin_rgb(spec.get("color_temp_k") or 4500)
        data.color = rgb
        obj = bpy.data.objects.new(data.name, data)
        off = Vector(spec["offset_from_camera_m"])
        obj.location = mw @ off
        obj["aidir.job_id"] = ir["job_id"]
        obj["aidir.role"] = "light"
        collection.objects.link(obj)


def _import_glb(path: str, collection):
    before = set(bpy.data.objects)
    kwargs = {"filepath": path}
    imported = False
    try:
        bpy.ops.import_scene.gltf("EXEC_DEFAULT", False, **kwargs)
        imported = True
    except Exception:
        imported = False
    if not imported:
        window = bpy.context.window
        area = None
        region = None
        if window and window.screen:
            for a in window.screen.areas:
                if a.type == "VIEW_3D":
                    area = a
                    region = next((r for r in a.regions if r.type == "WINDOW"), None)
                    break
        if area is None:
            return []
        with bpy.context.temp_override(window=window, area=area, region=region):
            bpy.ops.import_scene.gltf("EXEC_DEFAULT", False, **kwargs)
    new = [o for o in bpy.data.objects if o not in before]
    for obj in new:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return new


def _world_height(objects) -> float:
    import mathutils

    corners = []
    for obj in objects:
        if not getattr(obj, "bound_box", None):
            continue
        for c in obj.bound_box:
            corners.append(obj.matrix_world @ mathutils.Vector(c))
    if not corners:
        return 1.0
    return max(v.z for v in corners) - min(v.z for v in corners)


def _swap_glb(proxy, glb_objects, pose, collection, want_h=None):
    loc = pose["location_m"]
    yaw = pose["rotation_euler_rad"][2]
    if not glb_objects:
        return None
    empty = bpy.data.objects.new(proxy.name + ".glb", None)
    empty.location = loc
    empty.rotation_euler[2] = yaw
    empty["aidir.object_id"] = proxy.get("aidir.object_id")
    empty["aidir.job_id"] = proxy.get("aidir.job_id")
    collection.objects.link(empty)
    for obj in glb_objects:
        obj.parent = empty
    bpy.context.view_layer.update()
    native_h = _world_height(glb_objects)
    target = float(want_h or (proxy.dimensions.z if proxy else 2.0) or 2.0)
    if native_h > 0.05 and 0.05 < target / native_h < 25:
        empty.scale = (target / native_h,) * 3
    if proxy:
        bpy.data.objects.remove(proxy, do_unlink=True)
    return empty


def _instance_from(empty, pose, collection, name, job_id, oid):
    if empty is None:
        return None
    root = bpy.data.objects.new(name, None)
    root.location = pose["location_m"]
    root.rotation_euler[2] = pose["rotation_euler_rad"][2]
    root.scale = empty.scale.copy()
    root["aidir.object_id"] = oid
    root["aidir.job_id"] = job_id
    collection.objects.link(root)
    for child in empty.children:
        dup = child.copy()
        if child.data:
            dup.data = child.data
        collection.objects.link(dup)
        dup.parent = root
        dup.matrix_parent_inverse = child.matrix_parent_inverse.copy()
    return root


def _apply_hdri(path: str) -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("AIDIR_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def _walk(obj):
    yield obj
    for c in obj.children:
        yield from _walk(c)


def _hide_tree(obj, hide: bool) -> None:
    for o in _walk(obj):
        o.hide_set(hide)


def _world_min_z(obj) -> float:
    zs = []
    for o in _walk(obj):
        if o.type != "MESH" or not o.bound_box:
            continue
        mw = o.matrix_world
        zs.extend((mw @ Vector(c)).z for c in o.bound_box)
    return min(zs) if zs else obj.location.z


def _snap_collection(collection) -> None:
    scene = bpy.context.scene
    down = Vector((0.0, 0.0, -1.0))
    bpy.context.view_layer.update()
    roots = [
        o
        for o in collection.objects
        if not o.parent
        and o.get("aidir.role") not in ("shell", "camera", "light")
        and o.type in {"MESH", "EMPTY"}
    ]
    for obj in roots:
        _hide_tree(obj, True)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        hit, loc, *_rest = scene.ray_cast(dg, Vector((obj.location.x, obj.location.y, 200.0)), down)
        _hide_tree(obj, False)
        bpy.context.view_layer.update()
        if not hit:
            continue
        zmin = _world_min_z(obj)
        obj.location.z += loc.z - zmin + 0.002
    bpy.context.view_layer.update()


def _texture_shell(collection, ir: dict) -> None:
    surf = ir.get("surfaces") or {}
    ground = surf.get("ground") or {}
    path = surf.get("path") or {}
    wall = surf.get("wall") or {}
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        name = obj.name.lower()
        role = obj.get("aidir.role")
        cat = obj.get("aidir.category")
        if role == "shell" and ("wall" in name) and wall.get("diff_path"):
            mesh_util.apply_pbr(obj, "AIDIR_wall", wall.get("diff_path"), wall.get("nor_path"), wall.get("rough_path"), 4.0)
        elif role == "shell" and ground.get("diff_path") and any(k in name for k in ("ground", "floor", "sand", "deck", "dirt")):
            mesh_util.apply_pbr(obj, "AIDIR_ground", ground.get("diff_path"), ground.get("nor_path"), ground.get("rough_path"), 10.0)
        elif cat == "path" and path.get("diff_path"):
            mesh_util.apply_pbr(obj, "AIDIR_path", path.get("diff_path"), path.get("nor_path"), path.get("rough_path"), 8.0)


def apply_ir(ir: dict) -> None:
    job_id = ir["job_id"]
    wipe_job(job_id)
    col = _ensure_collection(job_id)
    kit = KITS.get(ir["domain"]) or KITS["generic"]
    kit(ir["world"], col, job_id)
    layout = ir["layout"]
    by_id = {o["id"]: o for o in ir["objects"]}
    proxies = {}
    for oid, pose in layout.items():
        proxies[oid] = spawn_part(ir, by_id[oid], pose, col)
    cam = _place_camera(ir, col)
    _place_lights(ir, cam, col)
    roots = {}
    for oid, spec in by_id.items():
        path = spec.get("cache_path")
        cid = spec.get("catalog_id")
        if not path:
            continue
        cat = spec.get("category") or ""
        want_h = FOOT.get(cat, (1, 1, 2))[2]
        raw = spec.get("real_size_m") or [0, 0, want_h]
        if float(raw[2]) > want_h * 0.4:
            want_h = float(raw[2])
        try:
            if cid and cid in roots:
                _instance_from(roots[cid], layout[oid], col, f"aidir.{oid}.glb", job_id, oid)
                proxy = proxies.get(oid)
                if proxy:
                    bpy.data.objects.remove(proxy, do_unlink=True)
                continue
            new = _import_glb(path, col)
            empty = _swap_glb(proxies.get(oid), new, layout[oid], col, want_h=want_h)
            if cid and empty is not None:
                roots[cid] = empty
        except Exception:
            continue
    hdri = ir.get("hdri") or {}
    hpath = hdri.get("cache_path") if isinstance(hdri, dict) else None
    try:
        apply_look(bpy.context.scene, hpath, float((hdri or {}).get("intensity") or 1.0))
    except Exception:
        if hpath:
            try:
                _apply_hdri(hpath)
            except Exception:
                pass
    bpy.context.view_layer.update()
    _texture_shell(col, ir)
    bpy.context.view_layer.update()
    _snap_collection(col)
    if ir.get("domain") in ("park", "forest", "zoo", "beach"):
        try:
            from .gn_scatter import scatter_on_ground

            ground = next((o for o in col.objects if o.get("aidir.role") == "shell" and o.type == "MESH"), None)
            inst = [
                o
                for o in col.objects
                if o.get("aidir.category") in ("bush", "plant") and o.type in {"EMPTY", "MESH"} and not o.parent
            ]
            dens = 0.45 if ir.get("domain") == "park" else 0.7
            scatter_on_ground(ground, inst, ir["job_id"], density=dens)
        except Exception:
            pass
    bpy.context.view_layer.update()
    bpy.context.scene.camera = cam
    log(f"apply job={job_id} objs={len(by_id)} glb={len(roots)}")
    try:
        for area in bpy.context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is None:
                continue
            with bpy.context.temp_override(area=area, region=region):
                bpy.ops.view3d.view_all(center=False)
            break
    except Exception:
        pass
    screen = getattr(bpy.context, "screen", None)
    if screen is not None:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.region_3d.view_perspective = "CAMERA"
                    break
