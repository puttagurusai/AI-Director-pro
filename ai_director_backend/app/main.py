from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.compile import compile_scene
from app.planner.domain import resolve_domain
from app.planner.groq_planner import GroqError, plan
from app.planner.heuristic import plan_heuristic

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"
INDEX = json.loads((FIXTURE_DIR / "index.json").read_text(encoding="utf-8"))

app = FastAPI(title="AI Director", version="0.1.0")
JOBS: dict[str, dict] = {}


class SceneIn(BaseModel):
    prompt: str = ""
    domain: str = "auto"


def _fixture_for(domain: str) -> dict:
    name = INDEX["domain_files"].get(domain) or INDEX["domain_files"]["generic"]
    path = FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _build_ir(prompt: str, ui_domain: str) -> dict:
    domain = resolve_domain(ui_domain, prompt)
    key = os.environ.get("GROQ_API_KEY", "").strip()
    source = "heuristic"
    if key:
        try:
            draft = plan(domain, prompt)
            source = "groq"
        except GroqError:
            draft = plan_heuristic(domain, prompt)
            source = "heuristic_after_groq"
    else:
        draft = plan_heuristic(domain, prompt)
    ir = compile_scene(draft, prompt)
    data = ir.model_dump(mode="json")
    data.setdefault("warnings", []).append(f"planner:{source}")
    return data


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "schema": "0.1",
        "groq": bool(os.environ.get("GROQ_API_KEY", "").strip()),
    }


@app.post("/v1/scenes", status_code=202)
def create_scene(body: SceneIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    try:
        ir = _build_ir(body.prompt, body.domain)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:400]) from exc
    job_id = ir["job_id"]
    JOBS[job_id] = ir
    return JSONResponse(
        status_code=202,
        content={"job_id": job_id, "status": ir.get("status") or "ready", "domain": ir["domain"]},
        headers={"Location": f"/v1/scenes/{job_id}"},
    )


@app.get("/v1/scenes/{job_id}")
def get_scene(job_id: str):
    ir = JOBS.get(job_id)
    if ir is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return ir


@app.get("/v1/scenes/{job_id}/events")
def events(job_id: str, since: int = 0):
    ir = JOBS.get(job_id)
    if ir is None:
        raise HTTPException(status_code=404, detail="unknown job")

    def gen():
        payload = json.dumps({"job_id": job_id, "status": "ready"})
        yield f"event: ir_ready\ndata: {payload}\n\n"
        yield f"event: complete\ndata: {payload}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
