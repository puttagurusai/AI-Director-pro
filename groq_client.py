"""Groq chat/completions — same pattern as llm_fw/config.json (Cloudflare-safe UA)."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

# Cloudflare error 1010 blocks the default Python-urllib User-Agent.
UA = (
    "TalkFace-llm_fw/1.0 (+https://github.com/local) "
    "Python-urllib compatible; Mozilla/5.0"
)

DEFAULT_BASE = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.1-8b-instant"
FALLBACK_MODELS = (
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "qwen/qwen3-32b",
)
_MODEL_CACHE: list[str] = []

_CONFIG_CANDIDATES = (
    Path(__file__).resolve().parent / "config.json",
    Path(__file__).resolve().parent / "ai_director_backend" / "config.json",
    Path(r"C:\me\proj\projface_v1\llm_fw\config.json"),
    Path(r"C:\me\proj\projface_v1\llm_fw\config.groq.json"),
)


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_config() -> dict:
    cfg = {"base_url": DEFAULT_BASE, "model": DEFAULT_MODEL, "api_key": ""}
    for path in _CONFIG_CANDIDATES:
        data = _read_json(path)
        if not data:
            continue
        if data.get("base_url"):
            cfg["base_url"] = str(data["base_url"]).rstrip("/")
        if data.get("model"):
            cfg["model"] = str(data["model"])
        key = str(data.get("api_key") or "").strip().strip('"').strip("'")
        if key.startswith("gsk_"):
            cfg["api_key"] = key
            break
    return cfg


def _headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": UA,
        "Accept": "application/json",
    }


def list_models(api_key: str) -> list[str]:
    """Models Groq will actually serve for this key (chat IDs only)."""
    global _MODEL_CACHE
    key = (api_key or "").strip()
    if not key:
        return list(FALLBACK_MODELS)
    cfg = load_config()
    url = cfg["base_url"] + "/models"
    headers = _headers(key)
    body = None
    try:
        import requests

        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        body = resp.json()
    except Exception:
        req = urllib.request.Request(url, method="GET")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception:
            body = None
    ids = []
    for row in (body or {}).get("data") or []:
        mid = str(row.get("id") or "")
        if not mid:
            continue
        low = mid.lower()
        if any(x in low for x in ("whisper", "tts", "guard", "prompt-guard")):
            continue
        ids.append(mid)
    ids = sorted(set(ids))
    if not ids:
        ids = list(FALLBACK_MODELS)
    _MODEL_CACHE = ids
    return ids


def cached_models() -> list[str]:
    return list(_MODEL_CACHE) if _MODEL_CACHE else list(FALLBACK_MODELS)


def chat(api_key: str, messages: list, *, model: str | None = None, temperature: float = 0.2, max_tokens: int = 2048, json_object: bool = False) -> dict:
    cfg = load_config()
    if not model:
        try:
            from .secrets import load_model

            model = load_model() or cfg["model"]
        except Exception:
            model = cfg["model"]
    url = cfg["base_url"] + "/chat/completions"
    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_object:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode("utf-8")
    headers = _headers(api_key)
    try:
        import requests

        resp = requests.post(url, data=data, headers=headers, timeout=90)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:240]}")
        return resp.json()
    except ImportError:
        pass
    except RuntimeError:
        raise
    except Exception:
        pass
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:240]
        raise RuntimeError(f"HTTP {exc.code}: {err}") from exc


def ping(api_key: str) -> tuple[str, str]:
    key = (api_key or "").strip()
    if not key:
        return "offline", "no saved Groq key"
    try:
        raw = chat(
            key,
            [{"role": "user", "content": "ping"}],
            max_tokens=4,
            json_object=False,
        )
        model = raw.get("model") or load_config()["model"]
        return "online", f"ok · {model}"
    except Exception as exc:
        return "offline", str(exc)[:100]
