"""Discovering Artifacts from a GitHub account.

Unauthenticated by default and limited to public Artifacts (FR-002). Whatever
could not be reached is reported, never silently truncated (FR-019).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

API = "https://api.github.com"
PAGE_SIZE = 100


@dataclass(frozen=True)
class Repository:
    name: str
    full_name: str
    clone_url: str
    html_url: str
    private: bool
    is_fork: bool
    upstream: str | None
    description: str | None
    pushed_at: str | None


@dataclass
class Discovery:
    """What a discovery run found, and what it could not reach."""

    repositories: list[Repository] = field(default_factory=list)
    unreachable: list[str] = field(default_factory=list)
    rate_limited: bool = False
    # Falso quando o token pertence a outra conta: só o que é público foi visto.
    account_is_authenticated: bool = True

    @property
    def complete(self) -> bool:
        return not self.unreachable and not self.rate_limited


class RateLimited(Exception):
    def __init__(self, reset_at: int | None = None):
        super().__init__("GitHub rate limit reached")
        self.reset_at = reset_at


def _request(url: str, token: str | None) -> tuple[list | dict, dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "dendrograph",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")), dict(response.headers)
    except urllib.error.HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        if exc.code in (403, 429) and remaining == "0":
            reset = exc.headers.get("X-RateLimit-Reset")
            raise RateLimited(int(reset) if reset else None) from exc
        raise


def _to_repository(raw: dict) -> Repository:
    parent = raw.get("parent") or {}
    return Repository(
        name=raw["name"],
        full_name=raw["full_name"],
        clone_url=raw["clone_url"],
        html_url=raw["html_url"],
        private=bool(raw.get("private")),
        is_fork=bool(raw.get("fork")),
        upstream=parent.get("full_name"),
        description=raw.get("description"),
        pushed_at=raw.get("pushed_at"),
    )


def authenticated_login(token: str, request=_request) -> str | None:
    """Which account the token belongs to, or None if it cannot be established."""
    try:
        payload, _ = request(f"{API}/user", token)
    except (RateLimited, urllib.error.HTTPError, urllib.error.URLError):
        return None
    if isinstance(payload, dict):
        return payload.get("login")
    return None


def discover(account: str, token: str | None = None, request=_request) -> Discovery:
    """Every repository the credentials can see for one account.

    Without a token this reaches public repositories only, at 60 requests an
    hour — fine for a demo, poor for a 500-repository archive (ADR-0008).
    """
    found = Discovery()
    # /user/repos vê os privados do próprio Author; /users/<a>/repos vê só públicos.
    # Só vale quando o token É desta conta: pedir github:outra-pessoa e receber os
    # próprios repositórios privados de volta seria varrer o que ninguém pediu.
    path = f"/users/{urllib.parse.quote(account)}/repos"
    if token:
        login = authenticated_login(token, request)
        if login and login.casefold() == account.casefold():
            path = "/user/repos"
        else:
            found.account_is_authenticated = False
    page = 1
    while True:
        url = f"{API}{path}?per_page={PAGE_SIZE}&page={page}&type=owner&sort=full_name"
        try:
            payload, _ = request(url, token)
        except RateLimited as limited:
            # Degrada relatando o que faltou. Truncar em silêncio seria pior que
            # falhar, porque o Author não veria a diferença na saída (FR-019).
            found.rate_limited = True
            found.unreachable.append(
                f"github:{account} (rate limited"
                + (f", resets at {_reset_text(limited.reset_at)}" if limited.reset_at else "")
                + f"; {len(found.repositories)} repositories reached before the limit)"
            )
            return found
        except urllib.error.HTTPError as exc:
            found.unreachable.append(f"github:{account} (HTTP {exc.code})")
            return found
        except urllib.error.URLError as exc:
            found.unreachable.append(f"github:{account} (unreachable: {exc.reason})")
            return found

        if not payload:
            break
        found.repositories.extend(_to_repository(raw) for raw in payload)
        if len(payload) < PAGE_SIZE:
            break
        page += 1
    return found


def _reset_text(epoch: int) -> str:
    return time.strftime("%H:%M UTC", time.gmtime(epoch))
