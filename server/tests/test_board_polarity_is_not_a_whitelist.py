"""The board tells us what NOT to work on, and that half must not become the whitelist.

The owner's standing priorities end with two refusals:

    "Finance/health/physics are ONLY test-beds, never the headline.
     Deprioritize generic meta-science, politics, cloud/trivia and off-domain topics."

Tokenized flat, those sentences contribute `finance`, `health`, `physic`, `generic`, `meta`,
`science`, `politic`, `cloud`, `trivia` to the on-priority set -- so a theme passes the gate on the
strength of the words that exist to exclude it. The brain's Lab door learned this and carries the
negative clause in `_BOARD_STOP`. The dungeon's quest gate kept a second, smaller stop-list and
never learned it: measured 2026-07-31 against the live board, ALL FIVE deprioritized subjects
passed, five for five.

The fix is one definition, published by the brain as `priority_terms` and consumed by the dungeon.
These tests pin the behaviour, not the spelling of the list.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution.methods import (_BOARD_STOP, _theme_tokens,  # noqa: E402
                                     board_priority_terms)

#: The shape of the real board text, held fixed here so the assertions do not drift when the owner
#: re-words his priorities. The live board is checked separately, for presence of the field only.
BOARD = (
    "OWNER'S STANDING PRIORITIES: frontier: Make inspeximus the #1 agent-memory product "
    "(numero uno). Prioritize research that COMPOUNDS into inspeximus's moat: agent-memory "
    "integrity (correction, supersession, revert, provable erasure, echo/poison resistance), "
    "recall and multi-hop retrieval quality measured vs mem0/Zep/Cognee, and the buyer-facing gap "
    "roadmap. Every finding must answer: does this make inspeximus better or prove a competitor "
    "gap? Finance/health/physics are ONLY test-beds, never the headline. Deprioritize generic "
    "meta-science, politics, cloud/trivia and off-domain topics."
)


def terms(text: str = BOARD) -> set:
    return board_priority_terms(text)


def passes(theme: str, allowed: set | None = None) -> bool:
    """The gate's actual rule, both sides of the bridge: any shared token admits the theme."""
    return bool(_theme_tokens(theme) & (terms() if allowed is None else allowed))


# --------------------------------------------------------------------------------------------
# the refusals must not admit anything
# --------------------------------------------------------------------------------------------

DEPRIORITIZED = [
    ("politics of central bank independence", "politics"),
    ("generic meta-science reform proposals", "generic meta-science"),
    ("cloud cost trivia for storage tiers", "cloud/trivia"),
    ("finance: volatility drag in leveraged ETFs", "finance is a test-bed, never the headline"),
    ("physics of spin-orbit coupling in 2D materials", "physics is a test-bed"),
    ("health span and longevity interventions", "health is a test-bed"),
]


def test_no_deprioritized_subject_passes_the_gate():
    admitted = [(t, sorted(_theme_tokens(t) & terms())) for t, _ in DEPRIORITIZED]
    admitted = [(t, hits) for t, hits in admitted if hits]
    assert not admitted, (
        "the board's own refusal words admitted %d theme(s) it exists to exclude: %s"
        % (len(admitted), admitted))


# --------------------------------------------------------------------------------------------
# ...and the frontier must still get through, or the gate is just closed
# --------------------------------------------------------------------------------------------

FRONTIER = [
    "supersession and provable erasure in agent memory",
    "multi-hop retrieval quality measured against mem0",
    "echo and poison resistance in a recall pipeline",
    "the buyer-facing gap roadmap for inspeximus",
]


def test_the_frontier_still_passes():
    """A stop-list wide enough to block everything would pass the test above and starve the swarm."""
    blocked = [t for t in FRONTIER if not passes(t)]
    assert not blocked, "the gate now refuses on-frontier work: %s" % blocked


def test_the_terms_are_not_empty():
    assert len(terms()) >= 15, "too few on-priority terms to gate anything: %s" % sorted(terms())


# --------------------------------------------------------------------------------------------
# the endpoint has to actually publish it, or the dungeon silently keeps its own copy
# --------------------------------------------------------------------------------------------

def test_the_board_endpoint_publishes_priority_terms():
    """The dungeon consumes this field; without it, it falls back to the flat read that was the bug."""
    import inspect

    from agora.api import agent_os_api
    src = inspect.getsource(agent_os_api.brain_board)
    assert "priority_terms" in src, "the board endpoint stopped publishing priority_terms"
    assert "_BOARD_STOP" in src, "priority_terms is no longer filtered through the polarity stop-list"


def test_the_negative_clause_is_actually_in_the_stop_list():
    """Belt and braces: the word-list defence stays, even though the sentence filter supersedes it."""
    for w in ("finance", "health", "physics", "politics", "cloud", "trivia", "generic", "meta"):
        assert w in _BOARD_STOP, "'%s' is a word the owner used to DEPRIORITIZE; it must not be a " \
                                 "priority term" % w


# --------------------------------------------------------------------------------------------
# the class, not the instance
# --------------------------------------------------------------------------------------------

def test_a_refusal_the_stop_list_never_heard_of_is_still_refused():
    """The guarantee, handed an input it cannot have been tuned for.

    The old defence was a hand-written list of forbidden nouns, and it had ALREADY rotted when this
    suite first ran: `science` was missing, so "generic meta-science" -- a phrase lifted verbatim
    from the deprioritize clause -- passed the gate on that token. A list of nouns has to be updated
    every time the owner re-words his priorities. The grammar of a refusal does not, so the filter
    now drops whole refusing SENTENCES. This board refuses three subjects nobody put on any list.
    """
    board = BOARD + " Deprioritize ornithology, numismatics and competitive yodelling."
    t = terms(board)
    for w in ("ornithology", "numismatics", "yodelling"):
        assert w not in t, "'%s' was refused by the board and became a priority term anyway" % w
    assert "erasure" in t, "the positive half of the board stopped contributing"


def test_the_boards_own_label_does_not_admit_a_subject():
    """`frontier` is how the board NAMES its priority, not a subject it names.

    The text opens "frontier: Make inspeximus the #1 agent-memory product", and task templates carry
    the same word, so it matched work against the board's own stationery. Measured on the live inbox
    2026-07-31: of 33 pending tasks, ELEVEN were classified on-board solely by this word, every one
    of them Bayesian-network structure learning -- a third of the queue, none of it on the memory
    frontier.
    """
    off = [
        "Crucible candidate: On the bnlearn benchmark networks (ALARM, INSURANCE, HEPAR-II)",
        "Research dossier: Using the Erdos-Renyi DAG generator from Zheng et al.",
        "Crucible candidate: minimum graph thinness in induced subgraphs",
    ]
    t = terms()
    assert "frontier" not in t, "the board's own label is a priority term again"
    admitted = [x for x in off if _theme_tokens(x) & t]
    assert not admitted, "structure-learning work was admitted to the memory frontier: %s" % admitted


def test_the_label_fix_does_not_cost_a_real_task():
    """The control that matters: the words the board names as SUBJECTS must keep admitting work.

    `roadmap` and `quality` each admitted a task on their own in the live measurement, which looks
    like the same boilerplate shape -- but the board names both as real subjects ("the buyer-facing
    gap roadmap", "retrieval quality measured vs mem0/Zep/Cognee"), so they stay.
    """
    for task in ("Synthesize roadmap: read /brain/roadmap-inputs",
                 "Measure multi-hop retrieval quality against mem0",
                 "Predict: bounded context for agents and their memory"):
        assert _theme_tokens(task) & terms(), "a real on-board task stopped passing: %s" % task


def test_the_fixture_would_leak_without_the_filter():
    """A control, because a green suite must not be able to mean 'the fixture has no refusals in it'.

    Runs the OLD flat derivation over the same board and asserts it DOES admit the deprioritized
    subjects. If this ever stops leaking, the fixture has lost its refusal clauses and every
    assertion above is passing vacuously.
    """
    flat = {w for w in _theme_tokens(BOARD) if w not in _BOARD_STOP}
    leaked = [t for t, _ in DEPRIORITIZED if _theme_tokens(t) & flat]
    assert leaked, "the fixture board carries no refusal words, so this suite proves nothing"
