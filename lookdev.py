"""Human Poly Haven look: HDRI is the light. No extra ML models."""

from __future__ import annotations

import bpy


def apply_look(scene, hdri_path: str | None, intensity: float = 1.0) -> None:
    try:
        if "BLENDER_EEVEE_NEXT" in dir(bpy.types) or True:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass
    view = scene.view_settings
    try:
        view.view_transform = "AgX"
    except TypeError:
        try:
            view.view_transform = "Filmic"
        except TypeError:
            pass
    view.look = "None"
    view.exposure = -0.15
    view.gamma = 1.0
    if hdri_path:
        world = scene.world or bpy.data.worlds.new("AIDIR_World")
        scene.world = world
        world.use_nodes = True
        nt = world.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputWorld")
        bg = nt.nodes.new("ShaderNodeBackground")
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri_path, check_existing=True)
        bg.inputs["Strength"].default_value = max(0.6, float(intensity) * 1.15)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
        # HDRI does the lighting; keep extra lamps dim.
        for obj in scene.objects:
            if obj.get("aidir.role") == "light" and obj.data and hasattr(obj.data, "energy"):
                obj.data.energy = min(float(obj.data.energy), 25.0)
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = "MATERIAL"
                space.shading.use_scene_world = True
                space.shading.use_scene_lights = True
                if scene.camera:
                    space.region_3d.view_perspective = "CAMERA"
