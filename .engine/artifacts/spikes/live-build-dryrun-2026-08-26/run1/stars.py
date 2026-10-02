"""Return a GitHub repository's star count.

Does NOT: authenticate, cache, rate-limit, retry, or open a socket itself.
The HTTP client is passed in so every failure path is testable without a network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

GITHUB = "https://api.github.com/repos/{owner}/{name}"

#: `Fetched.status` of 0 means the request never completed — DNS failure, refused
#: connection, timeout. It is not an HTTP status and must never be returned to a caller.
NO_ANSWER = 0


@dataclass(frozen=True)
class Fetched:
    """One upstream outcome. `status == NO_ANSWER` means there was no HTTP response."""

    status: int
    body: dict | None


class HttpClient(Protocol):
    def get(self, url: str) -> Fetched: ...


Reply = tuple[int, dict]


def get_repo_stars(owner: str, name: str, client: HttpClient) -> Reply:
    """Fetch the star count. Failures are returned as a Reply, never raised."""
    fetched = client.get(GITHUB.format(owner=owner, name=name))
    if fetched.status != 200:
        return _explain(fetched.status)
    return 200, {
        "owner": owner,
        "name": name,
        "stars": fetched.body["stargazers_count"],
    }


def _explain(upstream_status: int) -> Reply:
    """Map an upstream outcome onto a status of our own.

    A 404 is real information about the caller's request, so it passes through.
    Everything else is GitHub's problem, not the caller's, and becomes a 502 — the
    upstream status is never leaked.
    """
    if upstream_status == 404:
        return 404, {"error": "repository not found"}
    return 502, {"error": "github unavailable"}
