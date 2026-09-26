"""Stdlib SceneIR validator (JSON Schema subset + layout key equality)."""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "ir_schema.json"


class IRError(ValueError):
    def __init__(self, path: str, msg: str) -> None:
        super().__init__(f"{path}: {msg}")
        self.path = path


def _resolve_local(ref: str, defs: dict, root: dict) -> dict:
    if not ref.startswith("#/$defs/"):
        raise IRError("$ref", f"only local $defs refs allowed: {ref}")
    name = ref.split("/")[-1]
    if name not in defs:
        raise IRError("$ref", f"unknown def {name}")
    return defs[name]


def validate(instance, schema, defs=None, path="$", root=None):
    root = root if root is not None else schema
    defs = defs if defs is not None else schema.get("$defs", {})
    if "$ref" in schema:
        return validate(instance, _resolve_local(schema["$ref"], defs, root), defs, path, root)
    types = schema.get("type")
    if isinstance(types, list):
        errors = []
        for t in types:
            try:
                validate(instance, {**schema, "type": t}, defs, path, root)
                return
            except IRError as e:
                errors.append(str(e))
        raise IRError(path, "type union failed")
    t = types
    if t == "object":
        if not isinstance(instance, dict):
            raise IRError(path, "not object")
        extras_schema = schema.get("additionalProperties")
        props = schema.get("properties", {})
        if extras_schema is False:
            extra = set(instance) - set(props)
            if extra:
                raise IRError(path, "extra " + str(sorted(extra)))
        for k in schema.get("required", []):
            if k not in instance:
                raise IRError(path, "missing " + k)
        for k, sub in props.items():
            if k in instance:
                validate(instance[k], sub, defs, path + "." + k, root)
        if isinstance(extras_schema, dict):
            for k, val in instance.items():
                if k not in props:
                    validate(val, extras_schema, defs, path + "." + k, root)
    elif t == "array":
        if not isinstance(instance, list):
            raise IRError(path, "not array")
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise IRError(path, "minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise IRError(path, "maxItems")
        if "items" in schema:
            for i, el in enumerate(instance):
                validate(el, schema["items"], defs, f"{path}[{i}]", root)
    elif t == "string":
        if not isinstance(instance, str):
            raise IRError(path, "not string")
        if "enum" in schema and instance not in schema["enum"]:
            raise IRError(path, "enum")
        if "const" in schema and instance != schema["const"]:
            raise IRError(path, "const")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise IRError(path, "minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise IRError(path, "maxLength")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], instance):
            raise IRError(path, "pattern")
    elif t in ("number", "integer"):
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            raise IRError(path, "not number")
        if t == "integer" and int(instance) != instance:
            raise IRError(path, "not integer")
        if instance < schema.get("minimum", float("-inf")) or instance > schema.get("maximum", float("inf")):
            raise IRError(path, "range")
    elif t == "boolean":
        if not isinstance(instance, bool):
            raise IRError(path, "not bool")
    elif t == "null":
        if instance is not None:
            raise IRError(path, "not null")
    if "enum" in schema and t != "string" and instance not in schema["enum"]:
        raise IRError(path, "enum")


def validate_scene_ir(doc: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate(doc, schema)
    ids = {o["id"] for o in doc["objects"]}
    if set(doc["layout"]) != ids:
        raise IRError("layout", "keys must equal object ids")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
