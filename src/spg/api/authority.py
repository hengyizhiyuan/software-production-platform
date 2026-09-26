"""Authenticated single-owner HTTP boundary for Watt self-dogfood.

The first deployment has one Human owner.  The resource and membership tables
leave an explicit seam for shared runtimes; this module does not claim general
enterprise IAM.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from time import time
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from spg.infrastructure.persistence.auth_schema import (
    authority_memberships, authority_resource_access,
)

ACTOR_ID = "human:owner"
ORGANIZATION_ID = "organization:default"
SESSION_SECONDS = 24 * 60 * 60
IDENTITY_KEYS = frozenset({"human_identity", "authority_identity", "actor_identity"})


def _session_value(secret: str) -> str:
    nonce = secrets.token_hex(16)
    issued = str(int(time()))
    payload = f"{ACTOR_ID}.{issued}.{nonce}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _valid_session(secret: str, value: str | None) -> bool:
    if value is None:
        return False
    parts = value.split(".")
    if len(parts) != 4 or parts[0] != ACTOR_ID:
        return False
    try:
        issued = int(parts[1])
    except ValueError:
        return False
    if issued > time() + 60 or time() - issued > SESSION_SECONDS:
        return False
    payload = ".".join(parts[:3])
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(parts[3], expected)


def _derive_identity(value):
    if isinstance(value, dict):
        return {key: ACTOR_ID if key in IDENTITY_KEYS else _derive_identity(item)
            for key, item in value.items()}
    if isinstance(value, list):
        return [_derive_identity(item) for item in value]
    return value


def _resource_in_path(path: str) -> tuple[str, str] | None:
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[0] != "api":
        return None
    kind = {"works": "work", "interactions": "interaction",
        "goals": "goal"}.get(parts[1])
    if parts[1] == "repository-assets" and len(parts) >= 4:
        kind = "repository"
    if kind is None:
        return None
    try:
        return kind, str(UUID(parts[2]))
    except ValueError:
        return None


def install_authority_boundary(api: FastAPI, *, database, settings) -> None:
    """Protect every product route and replace caller identity before DTO parsing."""
    if settings.auth_mode == "test-only-disabled":
        if "PYTEST_CURRENT_TEST" not in os.environ:
            raise RuntimeError("test-only-disabled auth is available only inside pytest")
        return
    configured = settings.operator_token
    secret = None if configured is None else configured.get_secret_value()
    if secret is None or len(secret) < 32:
        raise RuntimeError("SPG_OPERATOR_TOKEN (at least 32 characters) is required")

    @api.post("/auth/session", include_in_schema=False)
    async def login(request: Request):
        body = await request.json()
        supplied = body.get("token") if isinstance(body, dict) else None
        if not isinstance(supplied, str) or not hmac.compare_digest(supplied, secret):
            return JSONResponse({"code": "INVALID_CREDENTIAL"}, status_code=401)
        response = JSONResponse({"actor_id": ACTOR_ID,
            "organization_id": ORGANIZATION_ID})
        response.set_cookie("watt_session", _session_value(secret),
            max_age=SESSION_SECONDS, httponly=True, samesite="strict",
            secure=request.url.scheme == "https", path="/")
        return response

    @api.get("/login", include_in_schema=False)
    async def login_page():
        return HTMLResponse("""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Watt sign in</title><main><h1>Watt sign in</h1>
<form id="login"><label>Operator token <input name="token" type="password"
autocomplete="current-password" required></label><button>Sign in</button></form>
<p id="error" role="alert"></p></main><script>
document.getElementById('login').addEventListener('submit', async event => {
  event.preventDefault(); const token = new FormData(event.target).get('token');
  const response = await fetch('/auth/session', {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify({token})});
  if (response.ok) location.assign('/app');
  else document.getElementById('error').textContent = 'Sign in failed';
});</script></html>""")

    @api.get("/auth/session", include_in_schema=False)
    async def current_actor():
        return {"actor_id": ACTOR_ID, "organization_id": ORGANIZATION_ID}

    @api.middleware("http")
    async def authority_middleware(request: Request, call_next):
        path = request.url.path
        if path in {"/health", "/login"} or path.startswith("/assets/") or (
            path == "/auth/session" and request.method == "POST"
        ):
            return await call_next(request)
        bearer = request.headers.get("authorization", "")
        token = bearer[7:] if bearer.startswith("Bearer ") else None
        bearer_valid = token is not None and hmac.compare_digest(token, secret)
        cookie_valid = _valid_session(secret, request.cookies.get("watt_session"))
        if not (bearer_valid or cookie_valid):
            if path in {"/", "/app", "/delivery"}:
                return RedirectResponse("/login", status_code=303)
            return JSONResponse({"code": "AUTHENTICATION_REQUIRED",
                "message": "Sign in to Watt"}, status_code=401)
        if cookie_valid and not bearer_valid and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != str(request.base_url).rstrip("/"):
                return JSONResponse({"code": "INVALID_ORIGIN"}, status_code=403)
        with database.unit_of_work() as uow:
            owner = uow.session.execute(select(authority_memberships.c.role).where(
                authority_memberships.c.organization_id == ORGANIZATION_ID,
                authority_memberships.c.actor_id == ACTOR_ID)).scalar_one_or_none()
            resource = _resource_in_path(path)
            access = None if resource is None else uow.session.execute(
                select(authority_resource_access.c.role).where(
                    authority_resource_access.c.resource_kind == resource[0],
                    authority_resource_access.c.resource_id == resource[1],
                    authority_resource_access.c.actor_id == ACTOR_ID,
                )).scalar_one_or_none()
        if owner != "OWNER" or (resource is not None and access != "OWNER"):
            return JSONResponse({"code": "ACCESS_DENIED"}, status_code=403)
        request.state.actor_id = ACTOR_ID
        if request.method not in {"GET", "HEAD", "OPTIONS"} and (
            "application/json" in request.headers.get("content-type", "")
        ):
            original = await request.body()
            try:
                value = json.loads(original)
            except (ValueError, UnicodeDecodeError):
                value = None
            if isinstance(value, (dict, list)):
                derived = json.dumps(_derive_identity(value),
                    separators=(",", ":")).encode("utf-8")
                request._body = derived
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store" if path.startswith("/api/") else response.headers.get("Cache-Control", "no-cache")
        return response
