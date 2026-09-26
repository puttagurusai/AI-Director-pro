"""Irregular ground: only the road/path strip is planar."""

from __future__ import annotations

import math
import random

import bmesh
import bpy

from .mesh_util import GROUND_RGB, _mat


def _noise(x: float, y: float, seed: int) -> float:
    rng = random.Random(seed ^ (int(x * 13) * 10007) ^ (int(y * 17) * 10009))
    n = 0.0
    amp, freq = 1.0, 0.07
    for _ in range(4):
        # value-noise via hash of cell
        ix, iy = math.floor(x * freq), math.floor(y * freq)
        fx, fy = (x * freq) - ix, (y * freq) - iy
        def h(a, b):
            r = random.Random((seed + a * 131 + b * 9176) & 0xFFFFFFFF)
            return r.random() * 2 - 1
        v00, v10, v01, v11 = h(ix, iy), h(ix + 1, iy), h(ix, iy + 1), h(ix + 1, iy + 1)
        sx = fx * fx * (3 - 2 * fx)
        sy = fy * fy * (3 - 2 * fy)
        n += amp * ((v00 * (1 - sx) + v10 * sx) * (1 - sy) + (v01 * (1 - sx) + v11 * sx) * sy)
        amp *= 0.45
        freq *= 2.05
    return n


def build_ground(
    name: str,
    wx: float,
    wy: float,
    collection,
    props: dict,
    ground_kind: str,
    amp: float,
    path_half: float,
    seed: str,
    nx: int = 72,
    ny: int = 54,
):
    """Grid terrain. |x-wx/2| < path_half stays z=0 (the road)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    s = abs(hash(seed)) % 100000
    verts = []
    for iy in range(ny + 1):
        row = []
        for ix in range(nx + 1):
            x = ix / nx * wx
            y = iy / ny * wy
            dx = abs(x - wx / 2.0)
            if path_half > 0.05 and dx < path_half + 0.35:
                z = 0.0
            elif amp <= 0.001:
                z = 0.0
            else:
                fade = 1.0
                if path_half > 0.05:
                    fade = min(1.0, max(0.0, (dx - path_half - 0.35) / 5.0))
                z = fade * amp * _noise(x, y, s)
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
    for iy in range(ny):
        for ix in range(nx):
            bm.faces.new((verts[iy][ix], verts[iy][ix + 1], verts[iy + 1][ix + 1], verts[iy + 1][ix]))
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            v = loop.vert.co
            loop[uv_layer].uv = (v.x / max(wx, 1.0), v.y / max(wy, 1.0))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0.0, 0.0, 0.0)
    rgba = GROUND_RGB.get(ground_kind, GROUND_RGB["grass"])
    obj.data.materials.append(_mat("AIDIR_" + name[:18], rgba))
    for k, v in props.items():
        obj[k] = v
    collection.objects.link(obj)
    return obj
