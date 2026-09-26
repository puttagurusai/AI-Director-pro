import bpy

from .groq_client import cached_models
from .secrets import clear_key, has_key, last4, save_key, save_model


def _on_key_edit(self, context):
    val = (self.groq_api_key or "").strip()
    if len(val) >= 8:
        save_key(val)
        self.groq_api_key = ""


class AIDIR_OT_clear_groq_key(bpy.types.Operator):
    bl_idname = "aidir.clear_groq_key"
    bl_label = "Remove saved Groq key"

    def execute(self, context):
        clear_key()
        self.report({"INFO"}, "Groq key removed from this PC")
        return {"FINISHED"}


class AIDIR_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ or "ai_director"

    groq_api_key: bpy.props.StringProperty(
        name="Groq API key",
        description="Paste once. Saved hidden on this PC, not in the .blend. Dots hide the characters.",
        default="",
        subtype="PASSWORD",
        options={"SKIP_SAVE"},
        update=_on_key_edit,
    )

    def _model_items(self, context):
        items = []
        for m in cached_models():
            items.append((m, m, m))
        if not items:
            items = [("openai/gpt-oss-20b", "openai/gpt-oss-20b", "")]
        return items

    groq_model: bpy.props.EnumProperty(
        name="Groq model",
        description="Chat model from your Groq account",
        items=_model_items,
        update=lambda self, context: save_model(self.groq_model),
    )

    def draw(self, context):
        layout = self.layout
        if has_key():
            layout.label(text=f"Groq key saved (hidden) · …{last4()}", icon="LOCKED")
            layout.operator("aidir.clear_groq_key", icon="X")
            layout.label(text="Paste a new key below only to replace it")
        else:
            layout.label(text="No Groq key yet — paste once, it stays on this PC")
        layout.prop(self, "groq_api_key", text="Groq API key")
        layout.prop(self, "groq_model", text="Groq model")
        layout.operator("aidir.refresh_models", icon="FILE_REFRESH")
        layout.label(text="Characters are hidden. Not stored in .blend files.")
        layout.label(text="Poly Haven: no key")
