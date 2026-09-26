"""AI Director — SceneIR compiler. Never exec model Python."""

from .job_modal import AIDIR_OT_apply_scene
from .prefs import AIDIR_AddonPreferences, AIDIR_OT_clear_groq_key
from .ui.panel import AIDIR_OT_check_apis, AIDIR_OT_refresh_models, AIDIR_PT_main_panel

import bpy

bl_info = {
    "name": "AI Director",
    "blender": (4, 2, 0),
    "category": "3D View",
}

DOMAINS = (
    ("auto", "Auto (from prompt)", "Infer park, city, space, interior, … from the sentence"),
    ("interior", "Interior", "Room / living space"),
    ("park", "Park", "Paths, trees, benches"),
    ("forest", "Forest", "Clearing and foliage"),
    ("city", "City", "Street and building masses"),
    ("zoo", "Zoo", "Enclosures and animal proxies"),
    ("space", "Space", "Station deck"),
    ("beach", "Beach", "Sand and water"),
    ("generic", "Generic", "Flat ground"),
)

classes = (
    AIDIR_AddonPreferences,
    AIDIR_OT_clear_groq_key,
    AIDIR_OT_apply_scene,
    AIDIR_OT_check_apis,
    AIDIR_OT_refresh_models,
    AIDIR_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ai_director_domain = bpy.props.EnumProperty(
        name="Domain",
        description="World type to generate",
        items=DOMAINS,
        default="auto",
    )
    bpy.types.Scene.ai_prompt = bpy.props.StringProperty(
        name="Prompt",
        description="Describe the scene",
        default="A park at dusk with a path, benches, and trees",
        maxlen=1024,
    )
    bpy.types.Scene.ai_director_job_id = bpy.props.StringProperty(
        name="Last job",
        default="",
    )
    bpy.types.Scene.ai_director_randomness = bpy.props.FloatProperty(
        name="Randomness",
        description="0 = same layout/assets every time. 1 = shuffle picks, scatter, yaw, HDRI/textures.",
        default=0.55,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )

    def _boot_ping():
        try:
            from .status import ping_polyhaven, ping_groq
            ping_polyhaven()
            mod = __package__ or "ai_director"
            ad = bpy.context.preferences.addons.get(mod)
            if ad is None:
                for k, a in bpy.context.preferences.addons.items():
                    if k.endswith(".ai_director"):
                        ad = a
                        break
            from .secrets import load_key, save_key

            if ad:
                typed = (ad.preferences.groq_api_key or "").strip()
                if typed:
                    save_key(typed)
                    ad.preferences.groq_api_key = ""
            ping_groq(load_key())
            from .groq_client import list_models

            list_models(load_key())
        except Exception:
            pass
        return None

    bpy.app.timers.register(_boot_ping, first_interval=0.8)


def unregister():
    del bpy.types.Scene.ai_director_domain
    del bpy.types.Scene.ai_prompt
    del bpy.types.Scene.ai_director_job_id
    del bpy.types.Scene.ai_director_randomness
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
