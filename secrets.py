"""Persist Groq key on this PC. Hidden, not in the .blend, survives addon reinstalls."""

from __future__ import annotations

import os
from pathlib import Path


def _dir() -> Path:
    try:
        import bpy

        root = Path(bpy.utils.user_resource("CONFIG", path="ai_director", create=True))
    except Exception:
        root = Path.home() / ".ai_director"
        root.mkdir(parents=True, exist_ok=True)
    return root


def key_path() -> Path:
    return _dir() / "groq.key"


def save_key(value: str) -> None:
    text = (value or "").strip()
    if not text:
        return
    path = key_path()
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def clear_key() -> None:
    path = key_path()
    if path.is_file():
        path.unlink()


def _clean(value: str) -> str:
    text = (value or "").strip().strip('"').strip("'")
    if text.lower() in {"api key", "api_key", "your_key", "gsk_xxx"}:
        return ""
    return text


def load_key() -> str:
    path = key_path()
    if path.is_file():
        text = _clean(path.read_text(encoding="utf-8"))
        if text:
            return text
    env = _clean(os.environ.get("GROQ_API_KEY", ""))
    if env:
        return env
    try:
        from .groq_client import load_config

        cfg_key = _clean(load_config().get("api_key") or "")
        if cfg_key:
            save_key(cfg_key)
            return cfg_key
    except Exception:
        pass
    return ""


def has_key() -> bool:
    return bool(load_key())


def model_path() -> Path:
    return _dir() / "groq_model.txt"


def save_model(name: str) -> None:
    text = (name or "").strip()
    if not text:
        return
    model_path().write_text(text, encoding="utf-8")


def load_model() -> str:
    path = model_path()
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    try:
        from .groq_client import DEFAULT_MODEL

        return DEFAULT_MODEL
    except Exception:
        return "llama-3.1-8b-instant"


def last4() -> str:
    k = load_key()
    if len(k) < 4:
        return ""
    return k[-4:]
