"""Does the dungeon still spend the model on speech bubbles, and did the fix silence the research?

WHY. The dungeon's `_converse` made THREE model calls per conversation. The product of those three
calls is one broadcast line of at most sixteen words, shown above an avatar. Nothing stores it,
nothing reads it, and the trust update that follows does not depend on it. It is the dungeon's twin
of the brain seminar, and it was invisible for the whole of its life because the dungeon carried no
spend meter until 2026-09-04.

WHAT THIS CHECKS:
  1. THE BUBBLE IS FREE BY DEFAULT. The `_llm_say` call inside `_converse` sits under
     `if _CHATTER_LLM:`, and `_CHATTER_LLM` reads an environment variable that defaults to off.
  2. THE WORLD IS STILL ALIVE. The `else` branch assigns the canned opener, so a conversation still
     produces a line, a broadcast and a trust update with no model call. A fix that empties the
     bubble is a different change from the one intended.
  3. THE RESEARCH PATHS ARE UNTOUCHED, and this is the control that matters. `_collaborate`,
     `_pipeline_tick`, `_run_debate` and `_run_red_team` must still reach a model unconditionally. If the
     flag reached them too, this probe would pass while the dungeon quietly stopped doing research,
     which is a worse outcome than the spend it was meant to stop.
  4. MUTATION. Moving the call out from under the guard must be caught, otherwise check 1 passes on
     any file at all.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DUNGEON = os.path.join(ROOT, "agora-game-server", "mcp_server.py")
OUT = os.path.join(HERE, "the_bubbles_are_free_and_the_research_still_pays.result.json")

# The functions that must KEEP spending: they produce grounded findings and advance the
# research pipeline. Names verified against the AST rather than recalled, because the first
# run of this probe named `_maybe_collaborate`, which schedules the work and never touches a
# model, so the control reported zero and refused. That refusal was the control working.
RESEARCH = ("_collaborate", "_pipeline_tick", "_run_debate", "_run_red_team")


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def guarded_calls(src, func, guard):
    """(model calls under `if <guard>:`, model calls not under it) inside `func`."""
    tree = ast.parse(src)
    target = next((n for n in ast.walk(tree)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func),
                  None)
    if target is None:
        refuse("no function %r in the dungeon; this check cannot see its subject" % func)
    under, plain = [], []
    def walk(node, inside):
        for child in ast.iter_child_nodes(node):
            now = inside
            if isinstance(child, ast.If) and isinstance(child.test, ast.Name) \
                    and child.test.id == guard:
                for b in child.body:
                    walk(b, True)
                for b in child.orelse:
                    walk(b, False)
                continue
            if isinstance(child, ast.Call):
                fn = child.func
                nm = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if nm in ("_llm_say", "_llm_say_sync", "_llm_content_sync", "_llm_prose_sync"):
                    (under if now else plain).append(child.lineno)
            walk(child, now)
    walk(target, False)
    return under, plain


def main():
    if not os.path.isfile(DUNGEON):
        refuse("no mcp_server.py at %s, so this check would pass by seeing nothing" % DUNGEON)
    src = io.open(DUNGEON, encoding="utf-8", errors="replace").read()

    # 1 — the default
    default_off = '_CHATTER_LLM = os.getenv("DUNGEON_CHATTER_LLM", "0")' in src
    print("  _CHATTER_LLM defaults to OFF: %s" % default_off)
    if not default_off:
        refuse("_CHATTER_LLM is missing or does not default to off")

    under, plain = guarded_calls(src, "_converse", "_CHATTER_LLM")
    print("  _converse: %d model call(s) under the guard, %d outside it" % (len(under), len(plain)))
    if plain:
        refuse("_converse still reaches a model outside the guard at line(s) %s" % plain)
    if not under:
        refuse("no model call under the guard either; the chatter path was removed rather than "
               "gated, so turning the flag on would do nothing")

    # 2 — the bubble still gets a line
    tree = ast.parse(src)
    conv = next(n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_converse")
    has_else = any(isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                   and n.test.id == "_CHATTER_LLM" and n.orelse for n in ast.walk(conv))
    print("  the off branch still assigns a canned line: %s" % has_else)
    if not has_else:
        refuse("the guard has no else branch, so with the flag off the conversation produces no "
               "line at all and the world goes silent")

    # 3 — THE CONTROL: research must still reach a model unconditionally
    print()
    for fn in RESEARCH:
        u, p = guarded_calls(src, fn, "_CHATTER_LLM")
        print("  CONTROL %-20s %d unconditional model call(s), %d behind the chatter flag"
              % (fn, len(p), len(u)))
        if u:
            refuse("%s is behind the chatter flag; the fix would silence research, not chatter" % fn)
        if not p:
            refuse("%s reaches no model at all; either it was broken or this probe is looking at "
                   "the wrong function, and a control that cannot fire proves nothing" % fn)

    # 4 — mutation
    mutant = src.replace("            if _CHATTER_LLM:\n", "            if True:\n", 1)
    if mutant == src:
        refuse("the mutation could not be applied, so control 4 never ran")
    mu, mp = guarded_calls(mutant, "_converse", "_CHATTER_LLM")
    print()
    if not mp:
        refuse("the mutation was not caught: a model call moved out from under the guard still "
               "reads as guarded, so check 1 would pass on an ungated file")
    print("  MUTATION: an unguarded model call in _converse was caught at line %d" % mp[0])

    print()
    print("  VERDICT: bubbles cost nothing, the world still talks, research still spends.")
    json.dump({"script": os.path.basename(__file__),
               "chatter_calls_guarded": under, "chatter_calls_unguarded": plain,
               "default_off": default_off, "canned_else_branch": has_else,
               "research_unconditional": {f: len(guarded_calls(src, f, "_CHATTER_LLM")[1])
                                          for f in RESEARCH},
               "mutation_caught_at": mp[0],
               "verdict": "CHATTER_IS_FREE"},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
