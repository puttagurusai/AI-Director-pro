"""bmesh helpers — never bpy.ops."""

from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Vector


GROUND_RGB = {
    "floor": (0.42, 0.40, 0.38, 1.0),
    "grass": (0.22, 0.38, 0.18, 1.0),
    "dirt": (0.28, 0.20, 0.12, 1.0),
    "pavement": (0.32, 0.32, 0.34, 1.0),
    "sand": (0.62, 0.54, 0.38, 1.0),
    "water_edge": (0.62, 0.54, 0.38, 1.0),
    "metal_deck": (0.18, 0.20, 0.24, 1.0),
    "void": (0.04, 0.04, 0.06, 1.0),
}

PART_RGB = {
    "slab": (0.40, 0.40, 0.42, 1.0),
    "beam": (0.22, 0.20, 0.18, 1.0),
    "cover": (0.45, 0.42, 0.38, 1.0),
    "mass": (0.48, 0.46, 0.44, 1.0),
    "pole": (0.25, 0.25, 0.28, 1.0),
    "board": (0.55, 0.50, 0.40, 1.0),
    "seat": (0.35, 0.26, 0.18, 1.0),
    "puddle": (0.12, 0.22, 0.32, 1.0),
    "foliage": (0.16, 0.34, 0.14, 1.0),
    "enclosure": (0.50, 0.48, 0.36, 1.0),
    "module": (0.55, 0.58, 0.62, 1.0),
    "proxy_box": (0.55, 0.45, 0.30, 1.0),
    "proxy_cylinder": (0.40, 0.50, 0.35, 1.0),
    "proxy_sphere": (0.25, 0.35, 0.55, 1.0),
}


def _mat(name: str, rgba) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    nt = mat.node_tree
    if nt:
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def _link(obj, collection, props):
    for k, v in props.items():
        obj[k] = v
    collection.objects.link(obj)
    return obj


def make_box(name, sx, sy, sz, location, collection, props, rgba=None, origin_ground=True):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
        if origin_ground:
            v.co.z += sz / 2.0
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    color = rgba or PART_RGB.get("mass", (0.5, 0.5, 0.5, 1.0))
    obj.data.materials.append(_mat("AIDIR_" + name[:20], color))
    return _link(obj, collection, props)


def make_icosphere(name, radius, location, collection, props, rgba=None):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.data.materials.append(_mat("AIDIR_" + name[:20], rgba or PART_RGB["proxy_sphere"]))
    return _link(obj, collection, props)


def make_cone(name, radius, depth, location, collection, props, rgba=None):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=radius, radius2=0.02, depth=depth)
    for v in bm.verts:
        v.co.z += depth / 2.0
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.data.materials.append(_mat("AIDIR_" + name[:20], rgba or PART_RGB["foliage"]))
    return _link(obj, collection, props)


def apply_pbr(obj, name: str, diff_path: str, nor_path: str | None = None, rough_path: str | None = None, repeat: float = 6.0) -> None:
    if obj is None or obj.type != "MESH" or not diff_path:
        return
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    texc = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (repeat, repeat, repeat)
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(diff_path, check_existing=True)
    img.image.colorspace_settings.name = "sRGB"
    nt.links.new(texc.outputs["UV"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], img.inputs["Vector"])
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    if nor_path:
        nimg = nt.nodes.new("ShaderNodeTexImage")
        nimg.image = bpy.data.images.load(nor_path, check_existing=True)
        nimg.image.colorspace_settings.name = "Non-Color"
        nrm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(mapping.outputs["Vector"], nimg.inputs["Vector"])
        nt.links.new(nimg.outputs["Color"], nrm.inputs["Color"])
        nt.links.new(nrm.outputs["Normal"], bsdf.inputs["Normal"])
    if rough_path:
        rimg = nt.nodes.new("ShaderNodeTexImage")
        rimg.image = bpy.data.images.load(rough_path, check_existing=True)
        rimg.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mapping.outputs["Vector"], rimg.inputs["Vector"])
        nt.links.new(rimg.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def look_at(obj, target_xyz):
    loc = Vector(obj.location)
    tgt = Vector(target_xyz)
    direction = tgt - loc
    if direction.length < 1e-6:
        return
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def kelvin_rgb(temp_k: float):
    t = max(1000.0, min(12000.0, float(temp_k))) / 100.0
    if t <= 66:
        r = 1.0
        g = max(0.0, min(1.0, 0.390081578 * math.log(t) - 0.631841443))
    else:
        r = max(0.0, min(1.0, 1.292936186 * (t - 60) ** -0.133204759))
        g = max(0.0, min(1.0, 1.129806918 * (t - 60) ** -0.075514849))
    if t >= 66:
        b = 1.0
    elif t <= 19:
        b = 0.0
    else:
        b = max(0.0, min(1.0, 0.543206789 * math.log(t - 10) - 1.196254089))
    return (r, g, b)
