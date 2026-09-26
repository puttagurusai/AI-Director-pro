"""Download Poly Haven gltf packages + HDRIs into Blender user cache."""

from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

import bpy

from .polyhaven import UA, files as ph_files, gltf_pack


def cache_dir() -> Path:
    root = Path(bpy.utils.user_resource("DATAFILES")) / "ai_director" / "cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _get_bytes(url: str) -> bytes:
    """dl.polyhaven.org 403s Python urllib (Cloudflare). curl succeeds on this PC."""
    import subprocess
    import tempfile

    tmp = Path(tempfile.gettempdir()) / "aidir_dl.bin"
    cmd = [
        "curl",
        "-fsSL",
        "--ssl-no-revoke",
        "--max-time",
        "90",
        "-A",
        "AIDirector/0.2 (Blender addon; https://polyhaven.com/our-api)",
        "-e",
        "https://polyhaven.com/",
        url,
        "-o",
        str(tmp),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 8:
        raise RuntimeError(f"cdn download failed: {proc.stderr[-200:] if proc.stderr else proc.returncode}")
    data = tmp.read_bytes()
    try:
        tmp.unlink()
    except Exception:
        pass
    return data


def fetch(url: str, suffix: str) -> Path | None:
    if not url:
        return None
    import hashlib

    name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24] + suffix
    dest = cache_dir() / name
    if dest.is_file() and dest.stat().st_size > 64:
        return dest
    dest.write_bytes(_get_bytes(url))
    return dest


def fetch_ph_model(ph_id: str) -> Path | None:
    dest = cache_dir() / ph_id
    main = dest / "model.gltf"
    if main.is_file() and main.stat().st_size > 32:
        return main
    pack = gltf_pack(ph_files(ph_id))
    if not pack:
        return None
    dest.mkdir(parents=True, exist_ok=True)
    for rel, url in pack:
        path = main if rel == "__main__" else dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.stat().st_size > 32:
            continue
        path.write_bytes(_get_bytes(url))
    return main if main.is_file() else None


def prefetch_ir(ir: dict) -> dict:
    seen = {}
    for obj in ir.get("objects") or []:
        cid = obj.get("catalog_id") or ""
        if not cid.startswith("ph_"):
            continue
        ph_id = cid[3:]
        if ph_id.startswith("hdri_"):
            continue
        try:
            if ph_id not in seen:
                seen[ph_id] = fetch_ph_model(ph_id)
            if seen[ph_id]:
                obj["cache_path"] = str(seen[ph_id])
            else:
                from .logutil import log
                log(f"ph miss {ph_id}")
        except Exception as exc:
            obj["cache_path"] = None
            from .logutil import log
            log(f"ph err {ph_id}: {exc}")
    for surf in (ir.get("surfaces") or {}).values():
        if not isinstance(surf, dict):
            continue
        for src, dst, suf in (
            ("diff_url", "diff_path", ".jpg"),
            ("nor_url", "nor_path", ".jpg"),
            ("rough_url", "rough_path", ".jpg"),
        ):
            url = surf.get(src)
            if not url:
                continue
            try:
                path = fetch(url, suf)
                if path:
                    surf[dst] = str(path)
            except Exception:
                pass
    hdri = ir.get("hdri") or {}
    url = hdri.get("asset_url") if isinstance(hdri, dict) else None
    if url:
        suffix = ".hdr" if ".hdr" in url.lower() else ".exr"
        try:
            path = fetch(url, suffix)
            if path:
                hdri["cache_path"] = str(path)
        except Exception:
            pass
    return ir
