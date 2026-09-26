import bpy

from ..status import LAST, ping_all

ADDON_VERSION = "0.4.2"


def _prefs(context):
    key = (__package__.rsplit(".", 1)[0] if __package__ and "." in __package__ else __package__) or "ai_director"
    addon = context.preferences.addons.get(key)
    if addon is None:
        for k, ad in context.preferences.addons.items():
            if k.endswith(".ai_director") or k == "ai_director":
                return ad.preferences
        return None
    return addon.preferences


def _line(layout, label, state, detail):
    icon = "CHECKMARK" if state == "online" else ("ERROR" if state == "offline" else "QUESTION")
    layout.label(text=f"{label}: {state.upper()} — {detail}", icon=icon)


class AIDIR_OT_check_apis(bpy.types.Operator):
    bl_idname = "aidir.check_apis"
    bl_label = "Check Groq + Poly Haven"
    bl_description = "Ping Groq (with your key) and the public Poly Haven API"

    def execute(self, context):
        from ..secrets import load_key

        ping_all(load_key())
        self.report({"INFO"}, f"Groq {LAST['groq']} ({LAST['groq_detail']}) · PH {LAST['ph']} ({LAST['ph_detail']})")
        return {"FINISHED"}


class AIDIR_OT_refresh_models(bpy.types.Operator):
    bl_idname = "aidir.refresh_models"
    bl_label = "Refresh Groq models"
    bl_description = "Fetch the chat models available on your Groq key"

    def execute(self, context):
        from ..groq_client import list_models
        from ..secrets import load_key, load_model, save_model

        ids = list_models(load_key())
        prefs = _prefs(context)
        current = load_model()
        if prefs and ids:
            if current not in ids:
                current = ids[0]
                save_model(current)
            try:
                prefs.groq_model = current
            except Exception:
                pass
        self.report({"INFO"}, f"{len(ids)} Groq models")
        return {"FINISHED"}


class AIDIR_PT_main_panel(bpy.types.Panel):
    bl_label = "AI Director"
    bl_idname = "AIDIR_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI Director"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = _prefs(context)
        layout.prop(scene, "ai_director_domain", text="Domain")
        layout.prop(scene, "ai_prompt", text="")
        layout.prop(scene, "ai_director_randomness", text="Randomness", slider=True)
        if prefs is not None:
            layout.prop(prefs, "groq_model", text="Groq model")
        layout.operator("aidir.refresh_models", icon="FILE_REFRESH")
        layout.operator("aidir.apply_scene", icon="WORLD")
        layout.separator()
        layout.operator("aidir.check_apis", icon="INFO")
        _line(layout, "Groq", LAST.get("groq", "unknown"), LAST.get("groq_detail", ""))
        _line(layout, "Poly Haven", LAST.get("ph", "unknown"), LAST.get("ph_detail", ""))
        layout.label(text="Powered by Poly Haven")
        if scene.ai_director_job_id:
            layout.label(text=f"Job {scene.ai_director_job_id[:12]}…")
        layout.separator()
        layout.label(text=f"AI Director v{ADDON_VERSION}")
