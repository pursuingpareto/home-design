"""OpenAPI generation (API-001 §8; D028).

FastAPI documents routes and response models. Request bodies are parsed strictly by the handlers,
so their schemas are added to `components` here from the same Pydantic models, together with the
five artifact payloads (an envelope's `payload` is typed by its `artifact_type`).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic.json_schema import models_json_schema

from homedesign.assemblies.schedule import AssemblySchedulePayload
from homedesign.estimating.estimate import PreliminaryEstimatePayload
from homedesign.estimating.pricebook import PriceBook
from homedesign.geometry.payloads import Mesh3dPayload, Plan2dPayload
from homedesign.timber.schedule import TimberSchedulePayload

REF_TEMPLATE = "#/components/schemas/{model}"
# Envelope payloads are typed per artifact_type (artifacts.md §5-8); named here so clients get their types.
PAYLOAD_COMPONENTS = (Plan2dPayload, Mesh3dPayload, TimberSchedulePayload, AssemblySchedulePayload, PreliminaryEstimatePayload)


def build_openapi(app: FastAPI) -> dict[str, Any]:
    from .routes import REQUEST_COMPONENTS

    document = get_openapi(title=app.title, version=app.version, summary=app.summary, routes=app.routes, separate_input_output_schemas=False)
    schemas = document.setdefault("components", {}).setdefault("schemas", {})
    models = (*REQUEST_COMPONENTS, PriceBook, *PAYLOAD_COMPONENTS)
    top, extra = models_json_schema([(m, "validation") for m in models], ref_template=REF_TEMPLATE)
    defs = dict(extra.get("$defs", {}))
    for model in models:  # RootModels are inlined by pydantic; give each a named component
        schema = top[(model, "validation")]
        if "$ref" not in schema:
            defs[model.__name__] = schema
    for name, schema in defs.items():
        if name in schemas and schemas[name] != schema:
            raise RuntimeError(f"OpenAPI component {name!r} would be defined twice with different schemas")
        schemas[name] = schema
    document["components"]["schemas"] = dict(sorted(schemas.items()))
    document["components"]["securitySchemes"] = {
        "bearer": {"type": "http", "scheme": "bearer", "description": "Development bearer tokens in VS-01 (D050)."}
    }
    document["security"] = [{"bearer": []}]
    return document


def install_openapi(app: FastAPI) -> None:
    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi(app)
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]
