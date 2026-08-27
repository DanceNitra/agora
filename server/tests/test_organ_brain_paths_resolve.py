"""Every brain path an organ names must reach a real endpoint.

`_brain_get_sync` builds `http://127.0.0.1:8000` + path, so a caller has to supply the whole
`/api/v1/agent-os/brain/...`. The organ contract handed authors the endpoints by their short names
(`/brain/gaps`, `/brain/canon-inputs`), and several wrote exactly that. Measured 2026-07-31 across
the shipped organs: artificer and cartographer prefixed correctly, king and thief probed for the
prefix at runtime, guard_l was mixed, and guard_r (8 paths), priest (8) and scholar (5) used the
bare form exclusively -- 404 on every read.

Those three are Dame Elara, High Priest Orin and Sage Mira: three of the four agents the acceptance
gate scored at zero. Sage Mira's cycle reported "no canon to curate (0 chars)" while
`/brain/canon-inputs` was serving 6,788 characters. The endpoint was healthy the whole time; the
request never arrived.

`_OrganCtx._api` now normalises both spellings in one place. This suite checks the stronger claim:
not merely that the two spellings agree, but that every path any organ actually names RESOLVES.
A typo'd endpoint fails here too.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ORGANS = REPO / "agora-game-server" / "organs"
MCP = REPO / "agora-game-server" / "mcp_server.py"
API_PREFIX = "/api/v1/agent-os"

sys.path.insert(0, str(REPO / "server"))

#: A string literal that looks like a brain path. Captures both spellings and ignores f-string tails.
_PATH_LITERAL = re.compile(r"""["'](/(?:api/v1/agent-os/)?brain/[a-zA-Z0-9\-_/]*)["']""")


def normalise(p: str) -> str:
    """The rule shipped in mcp_server._OrganCtx._api."""
    return API_PREFIX + p if p.startswith("/brain/") or p == "/brain" else p


def brain_routes() -> set:
    """Declared routes, read from the router module rather than the built app.

    `agora.main` registers this router at import time with no prefix of its own, but importing the
    app object alone yields only the docs routes -- the rest are attached during lifespan, which a
    unit test must not start. The router's own `routes` carry the full paths, so they are the honest
    source and cost nothing.
    """
    from agora.api.agent_os_api import router
    return {getattr(r, "path", "") for r in router.routes if "/brain" in getattr(r, "path", "")}


def organ_files() -> list:
    return sorted(f for f in ORGANS.glob("*.py") if f.name != "__init__.py")


def literals(f: Path) -> set:
    return set(_PATH_LITERAL.findall(f.read_text(encoding="utf-8", errors="replace")))


def matches_route(path: str, routes: set) -> bool:
    """Exact, or a route whose {param} segments the path fills."""
    if path in routes:
        return True
    segs = path.strip("/").split("/")
    for r in routes:
        rs = r.strip("/").split("/")
        if len(rs) == len(segs) and all(a == b or (a.startswith("{") and a.endswith("}"))
                                        for a, b in zip(rs, segs)):
            return True
    return False


@pytest.mark.parametrize("organ", [f.stem for f in organ_files()])
def test_every_path_this_organ_names_resolves(organ):
    routes = brain_routes()
    assert routes, "no brain routes found on the app; this suite cannot judge anything"
    f = ORGANS / (organ + ".py")
    bad = [p for p in sorted(literals(f)) if not matches_route(normalise(p), routes)]
    assert not bad, "%s names %d brain path(s) that resolve to nothing: %s" % (organ, len(bad), bad)


def test_the_normaliser_is_still_in_the_bridge():
    """Pins the rule to its one implementation, so the two cannot drift apart unnoticed."""
    src = MCP.read_text(encoding="utf-8", errors="replace")
    assert '_API_PREFIX = "/api/v1/agent-os"' in src, "the prefix constant is gone"
    assert "_brain_get_sync(self._api(path)" in src, "brain_get stopped normalising its path"
    assert "_brain_post_sync(self._api(path)" in src, "brain_post stopped normalising its path"


def test_the_bare_form_would_have_404d():
    """The control. Without it, a green suite could mean the fix works OR that nothing used the
    short form -- and the short form is exactly what three organs shipped."""
    routes = brain_routes()
    bare = {p for f in organ_files() for p in literals(f) if p.startswith("/brain/")}
    assert bare, "no organ uses the short form any more, so this suite proves nothing"
    assert not any(matches_route(p, routes) for p in bare), (
        "an unprefixed path resolves on its own; the prefix rule is not what makes these work")


def test_at_least_one_organ_still_uses_each_spelling():
    """Both spellings must stay exercised, or the normaliser silently stops being covered."""
    all_lits = {p for f in organ_files() for p in literals(f)}
    assert any(p.startswith("/brain/") for p in all_lits), "short form unused"
    assert any(p.startswith(API_PREFIX) for p in all_lits), "long form unused"
