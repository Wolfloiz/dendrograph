"""GitHub credentials: device flow first, `gh` as a shortcut, PAT for CI only.

Tokens are read from the environment, never written to config or the store, and
are read-only (Principle IV, ADR-0008).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

# Público por natureza: o fluxo de dispositivo não usa client_secret nem
# redirect URI, que é o que o mantém compatível com ADR-0004 (sem servidor).
CLIENT_ID = os.environ.get("DENDRO_GITHUB_CLIENT_ID", "")
SCOPE = "repo:status read:user"

TOKEN_VARIABLES = ("DENDRO_GITHUB_TOKEN", "GITHUB_TOKEN")


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    interval: int
    expires_in: int


def token_from_environment() -> str | None:
    """The only place a token is ever read from."""
    for name in TOKEN_VARIABLES:
        value = os.environ.get(name)
        if value:
            return value
    return None


def token_from_gh() -> str | None:
    """Borrow an authenticated `gh`. A convenience, never a requirement."""
    if not shutil.which("gh"):
        return None
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )
    except (subprocess.SubprocessError, OSError):
        return None
    token = result.stdout.strip()
    return token if result.returncode == 0 and token else None


def resolve_token() -> str | None:
    """The token for this run, or None to run unauthenticated against public data."""
    return token_from_environment() or token_from_gh()


def _post_form(url: str, fields: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={"Accept": "application/json", "User-Agent": "dendrograph"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AuthError(f"could not reach {url}: {exc}") from exc


def request_device_code(client_id: str = "") -> DeviceCode:
    client_id = client_id or CLIENT_ID
    if not client_id:
        raise AuthError(
            "no OAuth client id configured. Set DENDRO_GITHUB_CLIENT_ID, or run "
            "unauthenticated for public Artifacts."
        )
    payload = _post_form(DEVICE_CODE_URL, {"client_id": client_id, "scope": SCOPE})
    _raise_for_error(payload)
    return DeviceCode(
        device_code=payload["device_code"],
        user_code=payload["user_code"],
        verification_uri=payload["verification_uri"],
        interval=int(payload.get("interval", 5)),
        expires_in=int(payload.get("expires_in", 900)),
    )


def _raise_for_error(payload: dict) -> None:
    error = payload.get("error")
    if not error:
        return
    if error == "device_flow_disabled":
        # Verificado contra a documentação do GitHub em 2026-08-25 (ADR-0008):
        # o fluxo precisa ser habilitado nas configurações do app, uma vez.
        raise AuthError(
            "device flow is not enabled on this OAuth App. Enable it in the app's "
            "settings — it is a one-time setting on the app, not on the Author."
        )
    raise AuthError(payload.get("error_description", error))


def poll_for_token(
    code: DeviceCode, client_id: str = "", sleep=time.sleep, now=time.monotonic
) -> str:
    """Poll until the Author approves the code in their browser."""
    client_id = client_id or CLIENT_ID
    deadline = now() + code.expires_in
    interval = code.interval
    while now() < deadline:
        payload = _post_form(
            ACCESS_TOKEN_URL,
            {
                "client_id": client_id,
                "device_code": code.device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        error = payload.get("error")
        if error == "authorization_pending":
            sleep(interval)
            continue
        if error == "slow_down":
            interval = int(payload.get("interval", interval + 5))
            sleep(interval)
            continue
        _raise_for_error(payload)
        return payload["access_token"]
    raise AuthError("the device code expired before it was approved")


def instructions(code: DeviceCode) -> str:
    return (
        f"Open {code.verification_uri} and enter the code {code.user_code}\n"
        "Waiting for approval… (the token is never written to disk)"
    )
