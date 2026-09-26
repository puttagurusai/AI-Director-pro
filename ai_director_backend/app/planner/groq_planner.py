from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from app.ir.schema import PlannerDraft
from app.planner.prompt import SYSTEM, user_message

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqError(RuntimeError):
    pass


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("python"):
            raw = raw[6:]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise GroqError("no JSON object in model output")
    return json.loads(raw[start : end + 1])


def complete_json(messages: list[dict], api_key: str, model: str) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise GroqError(f"Groq HTTP {exc.code}: {detail}") from exc
    text = body["choices"][0]["message"]["content"]
    return _extract_json(text)


def plan(domain: str, prompt: str) -> PlannerDraft:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise GroqError("GROQ_API_KEY is not set")
    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_message(domain, prompt)},
    ]
    data = complete_json(messages, api_key, model)
    data["domain"] = domain
    data["schema_version"] = "0.1"
    try:
        return PlannerDraft.model_validate(data)
    except Exception as exc:
        repair = messages + [
            {"role": "assistant", "content": json.dumps(data)[:4000]},
            {
                "role": "user",
                "content": f"That JSON failed validation: {exc}. Return a corrected object only.",
            },
        ]
        data2 = complete_json(repair, api_key, model)
        data2["domain"] = domain
        data2["schema_version"] = "0.1"
        return PlannerDraft.model_validate(data2)
