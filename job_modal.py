"""Modal apply — Groq + Poly Haven inside the addon. No local server."""

from __future__ import annotations

import queue
import threading

import bpy

from .apply import apply_ir, wipe_job
from .catalog_cache import prefetch_ir
from .ir import IRError, validate_scene_ir
from .planner import build_scene, groq_status
from .secrets import load_key


class AIDIR_OT_apply_scene(bpy.types.Operator):
    bl_idname = "aidir.apply_scene"
    bl_label = "Generate Scene"
    bl_options = {"REGISTER", "UNDO"}
    _busy = False

    def invoke(self, context, event):
        if AIDIR_OT_apply_scene._busy:
            self.report({"WARNING"}, "Job already running")
            return {"CANCELLED"}
        AIDIR_OT_apply_scene._busy = True
        self.q: queue.Queue = queue.Queue()
        self.job_id = None
        self.done = False
        self._timer = None
        prompt = context.scene.ai_prompt
        domain = context.scene.ai_director_domain
        randomness = float(getattr(context.scene, "ai_director_randomness", 0.5) or 0.5)
        key = load_key()

        def run():
            try:
                ir = build_scene(prompt, domain, key, randomness=randomness)
                validate_scene_ir(ir)
                prefetch_ir(ir)
                self.q.put(("ir", ir))
            except Exception as exc:
                self.q.put(("err", str(exc)))

        threading.Thread(target=run, daemon=True).start()
        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC":
            if self.job_id:
                wipe_job(self.job_id)
            self._cleanup(context)
            return {"CANCELLED"}
        if event.type == "TIMER":
            try:
                self._drain(context)
            except Exception as exc:
                self.report({"ERROR"}, str(exc))
                if self.job_id:
                    wipe_job(self.job_id)
                self._cleanup(context)
                return {"CANCELLED"}
            if self.done:
                self._cleanup(context)
                return {"FINISHED"}
        return {"RUNNING_MODAL"}

    def _drain(self, context):
        try:
            kind, payload = self.q.get_nowait()
        except queue.Empty:
            return
        if kind == "err":
            raise RuntimeError(payload)
        if kind == "ir":
            self.job_id = payload["job_id"]
            context.scene.ai_director_job_id = self.job_id
            try:
                apply_ir(payload)
            except Exception as exc:
                from .logutil import log

                log(f"apply fail {exc}")
                raise
            self.done = True
            n = len(payload.get("objects") or [])
            ph = sum(1 for o in payload["objects"] if o.get("catalog_id") or o.get("cache_path"))
            st = groq_status(load_key())
            self.report({"INFO"}, f"{payload.get('domain')} · {n} objs · PH {ph} · Groq {st}")

    def _cleanup(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        AIDIR_OT_apply_scene._busy = False
