"""Shared HTTP test helpers: a TestClient that validates every response against the committed OpenAPI.

Used by the API-001 tests and the TEST-001 integration suite.
"""

from __future__ import annotations

import json
import re
from typing import Any

import jsonschema
from fastapi.testclient import TestClient

from homedesign.api.app import create_app
from homedesign.api.settings import Settings
from homedesign.model.schema_export import OPENAPI_PATH
from test_project import ACTOR, ACTOR_B, KEY, T0, cid

TOKENS = {"tok-a": ACTOR, "tok-b": ACTOR_B}
OPENAPI = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
POST_KEY, BEAM_KEY = "timber.POST.8x8", "timber.BEAM.8x12"
# Every line of Reference House 001 v2, timber (D053) and connection (ART-002 §7): a book with these rows is complete.
FULL_PRICES = {POST_KEY: 3150, BEAM_KEY: 4725, "timber.SILL.8x8": 3150, "timber.FLOOR_JOIST.4x8": 1200,
               "timber.PRINCIPAL_RAFTER.8x10": 3900, "timber.PURLIN.6x8": 2350, "timber.KNEE_BRACE.4x6": 900,
               "connection.BRIDLE": 6500, "connection.HOUSED_DOVETAIL": 3800, "connection.PEGGED_MORTISE_TENON": 4500,
               # ART-003 §7: the straw bale walls' layers (per m²) and bucks (per m), so the book stays complete.
               "assembly.straw-bale.bales": 2200, "assembly.straw-bale.clay-plaster": 3500, "assembly.straw-bale.lime-plaster": 4200,
               "wallframing.BUCK_HEAD.1.5x18": 1900, "wallframing.BUCK_JAMB.1.5x18": 1900, "wallframing.BUCK_SILL.1.5x18": 1900}
# The stud infill lines, for books that price both families (ART-003 §7.2).
STUD_INFILL_PRICES = {"assembly.stud-infill.siding": 5200, "assembly.stud-infill.sheathing": 1800, "assembly.stud-infill.framing": 1500,
                      "assembly.stud-infill.gypsum-board": 1600, "wallframing.CRIPPLE.2x6": 600, "wallframing.GIRT.2x6": 600,
                      "wallframing.HEADER.2x8": 800, "wallframing.JACK.2x6": 600, "wallframing.KING.2x6": 600, "wallframing.ROUGH_SILL.2x6": 600,
                      "wallframing.STUD.2x6": 600}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def schema_for(ref: str) -> dict[str, Any]:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": ref, "components": OPENAPI["components"]}


def conforms(component: str, value: Any) -> None:
    jsonschema.Draft202012Validator(schema_for(f"#/components/schemas/{component}")).validate(value)


def _operation(method: str, path: str) -> dict[str, Any]:
    path = path.split("?")[0]
    for template, operations in OPENAPI["paths"].items():
        if re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", template), path) and method.lower() in operations:
            return operations[method.lower()]
    raise AssertionError(f"{method} {path} is not in openapi.v1.json")


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self):
        return self.now


class Api:
    """A TestClient that checks each response against the OpenAPI document and the request-ID rules."""

    def __init__(self, app, clock: Clock) -> None:
        self.app, self.clock = app, clock
        self.client = TestClient(app)
        self.service = app.state.service

    def call(self, method: str, path: str, *, token: str | None = "tok-a", json_body: Any = None, raw: bytes | None = None, content_type: str = "application/json", headers: dict[str, str] | None = None):
        sent = dict(headers or {})
        if token is not None:
            sent["Authorization"] = f"Bearer {token}"
        if json_body is not None or raw is not None:
            sent["Content-Type"] = content_type
            raw = raw if raw is not None else json.dumps(json_body).encode()
        response = self.client.request(method, path, content=raw, headers=sent)
        request_id = response.headers.get("x-request-id", "")
        assert UUID_RE.match(request_id), response.headers
        documented = _operation(method, path)["responses"]
        spec = documented.get(str(response.status_code)) or documented["default"]
        body = response.json()
        jsonschema.Draft202012Validator(schema_for(spec["content"]["application/json"]["schema"]["$ref"])).validate(body)
        if response.status_code >= 400:
            assert body["error"]["request_id"] == request_id
        return response

    # shortcuts
    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.call("POST", path, json_body=body, **kw)

    def put(self, path, body=None, **kw):
        return self.call("PUT", path, json_body=body, **kw)

    # VS-01 flow helpers
    def create(self, token="tok-a") -> str:
        response = self.post("/api/v1/projects", {"command_id": cid(), "type": "CreateReferenceProject", "args": {}}, token=token)
        assert response.status_code == 201, response.json()
        return response.json()["project_id"]

    def head(self, pid) -> str:
        return self.get(f"/api/v1/projects/{pid}").json()["head_revision_id"]

    def snapshot(self, pid, rev=None) -> dict:
        return self.get(f"/api/v1/projects/{pid}/revisions/{rev or self.head(pid)}").json()

    def command(self, pid, type_, args, **kw) -> dict:
        return {"command_id": kw.get("command_id") or cid(), "project_id": pid, "base_revision_id": kw.get("base") or self.head(pid), "type": type_, "args": args}

    def width(self, pid, width, **kw) -> dict:
        footprint = next(e for e in self.snapshot(pid)["entities"] if e["kind"] == "Footprint")
        return self.command(pid, "SetFootprintDimensions", {"width_m": width, "depth_m": footprint["depth_m"]}, **kw)

    def routine(self, pid, n=0.5, **kw) -> dict:
        """A routine command (dependencies.md §4.1): AddSection, the only routine command since D057."""
        return self.command(pid, "AddSection", {"nominal_label": f"routine-{n}", "actual_width_m": 0.1, "actual_depth_m": 0.2}, **kw)

    def roof(self, pid, pitch=0.5, **kw) -> dict:
        """Consequential since D057: commit it with ``preview_commit``."""
        return self.command(pid, "SetGableRoofParameters", {"pitch_rad": pitch, "eave_overhang_m": 0.6096}, **kw)

    def preview(self, pid, command, **kw):
        return self.post(f"/api/v1/projects/{pid}/commands/preview", command, **kw)

    def commit(self, pid, command, preview_token=None, **kw):
        body = {"command": command} | ({"preview_token": preview_token} if preview_token else {})
        return self.post(f"/api/v1/projects/{pid}/commands/commit", body, **kw)

    def preview_commit(self, pid, command):
        token = self.preview(pid, command).json()["preview_token"]
        return self.commit(pid, command, token)


def make_api(store, registry=None, *, tokens: dict[str, str] | None = None, project_id_factory=None) -> Api:
    clock = Clock()
    settings = Settings(preview_key=KEY, store="memory", dev_tokens=tokens or TOKENS)
    return Api(create_app(settings, store=store, registry=registry, clock=clock, project_id_factory=project_id_factory), clock)


def book(**prices):
    return {
        "currency": "USD", "as_of": "2026-11-01", "source": "Supplier quote #123", "geography": "Chittenden County, VT",
        "rows": [{"key": key, "unit": unit_for(key), "unit_price_minor": price} for key, price in prices.items()],
    }


def unit_for(key: str) -> str:
    """The unit a key's family requires (ART-002 §7.3, ART-003 §7.2)."""
    return "each" if key.startswith("connection.") else "m2" if key.startswith("assembly.") else "m"
