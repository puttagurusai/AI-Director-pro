"""Live Groq + Poly Haven health checks. Never run on every panel redraw."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .groq_client import ping as groq_ping
from .polyhaven import API, UA

LAST = {
    "groq": "unknown",
    "groq_detail": "not checked",
    "ph": "unknown",
    "ph_detail": "not checked",
    "when": 0.0,
}


def ping_groq(api_key: str) -> tuple[str, str]:
    state, detail = groq_ping(api_key)
    LAST.update(groq=state, groq_detail=detail, when=time.time())
    return state, detail


def ping_polyhaven() -> tuple[str, str]:
    try:
        req = urllib.request.Request(
            API + "/search?q=bench&t=models&limit=3",
            headers={"User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        hits = body.get("results") or []
        if hits:
            slug = hits[0].get("slug") or "?"
            LAST.update(ph="online", ph_detail=f"ok · search hit {slug}")
        else:
            LAST.update(ph="offline", ph_detail="search returned 0")
    except urllib.error.HTTPError as exc:
        LAST.update(ph="offline", ph_detail=f"HTTP {exc.code}")
    except Exception as exc:
        LAST.update(ph="offline", ph_detail=str(exc)[:80])
    LAST["when"] = time.time()
    return LAST["ph"], LAST["ph_detail"]


def ping_all(api_key: str) -> dict:
    ping_groq(api_key)
    ping_polyhaven()
    return dict(LAST)
