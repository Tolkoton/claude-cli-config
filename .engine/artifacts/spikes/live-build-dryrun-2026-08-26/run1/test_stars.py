import unittest

from stars import NO_ANSWER, Fetched, get_repo_stars


class FakeClient:
    """Returns one canned outcome and records the URL it was asked for."""

    def __init__(self, outcome: Fetched) -> None:
        self.outcome = outcome
        self.asked: str | None = None

    def get(self, url: str) -> Fetched:
        self.asked = url
        return self.outcome


class ContractTest(unittest.TestCase):
    """Catches: a handler that returns the raw upstream body, or that builds the
    wrong upstream URL and happens to work against a fake that ignores it."""

    def test_returns_star_count_for_the_requested_repo(self) -> None:
        client = FakeClient(Fetched(200, {"stargazers_count": 4211, "id": 99}))

        status, body = get_repo_stars("astral-sh", "ruff", client)

        self.assertEqual(200, status)
        self.assertEqual({"owner": "astral-sh", "name": "ruff", "stars": 4211}, body)
        self.assertEqual("https://api.github.com/repos/astral-sh/ruff", client.asked)


class FailureMappingTest(unittest.TestCase):
    """Catches the naive implementation that passes the upstream status through:
    a GitHub 500 or a dead connection must not reach our caller as-is."""

    def test_dead_connection_becomes_bad_gateway(self) -> None:
        status, body = get_repo_stars("a", "b", FakeClient(Fetched(NO_ANSWER, None)))

        self.assertEqual(502, status)
        self.assertEqual({"error": "github unavailable"}, body)

    def test_upstream_server_error_becomes_bad_gateway(self) -> None:
        status, _ = get_repo_stars("a", "b", FakeClient(Fetched(500, None)))

        self.assertEqual(502, status)

    def test_unknown_repo_stays_a_not_found(self) -> None:
        status, body = get_repo_stars("a", "b", FakeClient(Fetched(404, None)))

        self.assertEqual(404, status)
        self.assertEqual({"error": "repository not found"}, body)


if __name__ == "__main__":
    unittest.main()
