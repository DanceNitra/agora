"""
ESS Stability Test — Swarm Invasion Proof

Based on Axelrod's Proposition 2 (1984):
  'TIT FOR TAT is collectively stable if the discount parameter w is
   sufficiently large relative to the payoff parameter.'

Experiment:
  Rounds 1..50      10 TFT agents only — mutual cooperation, trust settles.
  Round 51          inject 3 ALL-D defectors (always defect).
  Rounds 51..100    watch the invasion attempt.
  Expected          defectors are driven to ~0 trust and stay isolated, while
                    TFT agents BUILD high mutual trust with one another —
                    i.e. the defector strategy cannot invade.

Run:
  pytest agora/tests/test_ess_stability.py -v
  # or directly:
  python -m agora.tests.test_ess_stability

──────────────────────────────────────────────────────────────────────────────
NOTE — deviations from the original handoff code (all deliberate, see DONE handoff):
  1. `ESS_TOPICS` does not exist in ess_protocol → removed from imports.
  2. `pair_memory` is now PERSISTENT across rounds. In the handoff it was rebuilt
     inside every round, so a TFT agent never actually retaliated against a
     defector (the defector always moved second within a round, memory then wiped).
     That left TFT→defector trust == TFT→TFT trust → no separation → the test could
     not prove anything. Persistent memory gives real cross-round Tit-for-Tat.
  3. True injection at round 51 (defectors are inactive before then), matching the
     stated narrative rather than seeding everyone from round 1.
  4. The TrustEngine's forgiveness rule resets mutual-cooperation trust to BASELINE
     (0.3), so the handoff's `tft_tft > 0.3` assertion is mathematically impossible.
     The ESS criterion is therefore baseline-aware and separation-based:
        - TFT↔TFT trust stays at/above baseline (not destabilised below it), AND
        - TFT→defector trust collapses near 0, AND
        - the gap between them is large (defectors are clearly distinguished).
  5. The tables come from the ORM models, not from schema.sql. That file is not applied
     at runtime and had drifted from the models on 20 of 23 tables, which made this
     experiment unrunnable (datatype mismatch on trust_scores.id). See _make_db.
"""

import json
import os
import sys

import aiosqlite

try:
    import pytest
except ImportError:  # allow direct execution without pytest installed
    pytest = None

# Ensure we can import the project package when run as a file.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agora.coordination.ess_protocol import TrustEngine, ESSMessage  # noqa: E402

# ── Constants ──────────────────────────────────────
TFT_COUNT = 10            # Number of TFT agents in the swarm
DEFECTOR_COUNT = 3        # Number of invading defectors
COOPERATION_ROUNDS = 50   # Rounds before invasion
INVASION_ROUNDS = 50      # Rounds after invasion
TOTAL_ROUNDS = COOPERATION_ROUNDS + INVASION_ROUNDS

BASELINE = TrustEngine.BASELINE_TRUST  # 0.3

# NOTE: this used to read ../storage/schema.sql, which has since been DELETED. It never built any real
# database (ORM create_all does), it had drifted from the models on 20 of 23 tables, and six of its
# tables were defined three times over with IF NOT EXISTS so two thirds of those definitions were dead
# text. agora/storage/models.py is the schema. See _make_db.


# ── Agent factories ────────────────────────────────

def make_agent(agent_id: str, strategy: str) -> dict:
    priv, pub = ESSMessage.generate_keypair()
    return {
        "agent_id": agent_id,
        "role": strategy,
        "strategy": strategy,          # "tft" or "all_d"
        "private_key": priv,
        "public_key": pub,
    }


async def seed_agents(db, agents: list[dict]):
    """Insert agents into the DB with real Ed25519 public keys (task 1.5)."""
    for a in agents:
        pub_hex = ESSMessage.public_key_to_hex(a["public_key"])
        genome = json.dumps({"strategy": a["strategy"], "role": a["role"]})
        await db.execute(
            """INSERT OR IGNORE INTO agent_identities
               (agent_id, public_key, generation, genome, trust_score,
                energy_balance, role, status)
               VALUES (?, ?, 0, ?, 0.5, 100, ?, 'active')""",
            (a["agent_id"], pub_hex, genome, a["role"]),
        )
    await db.commit()


# ── One round ──────────────────────────────────────

async def run_round(engine, active_agents, pair_memory, round_num) -> dict:
    """Run one round: every active agent interacts with every other once.

    `pair_memory[(x, y)]` is x's last move toward y, persisted ACROSS rounds so
    Tit-for-Tat actually mirrors a partner's previous behaviour. TFT agents:
    cooperate unless the partner defected against them last time. Defectors
    (all_d) always defect.
    """
    ids = [a["agent_id"] for a in active_agents]
    strat = {a["agent_id"]: a["strategy"] for a in active_agents}

    for a_id in ids:
        for b_id in ids:
            if a_id == b_id:
                continue
            if strat[a_id] == "all_d":
                outcome = "defect"
            else:
                # TFT: mirror b's last move toward a (nice on first contact).
                b_last_vs_a = pair_memory.get((b_id, a_id))
                outcome = "defect" if b_last_vs_a == "defect" else "cooperate"

            await engine.record_interaction(a_id, b_id, outcome)
            pair_memory[(a_id, b_id)] = outcome

    return await _metrics(engine, active_agents, round_num)


async def _metrics(engine, active_agents, round_num) -> dict:
    tft_ids = [a["agent_id"] for a in active_agents if a["strategy"] == "tft"]
    def_ids = [a["agent_id"] for a in active_agents if a["strategy"] == "all_d"]

    tft_tft, tft_def, def_tft, def_all = [], [], [], []

    for tid in tft_ids:
        for pid in tft_ids:
            if tid != pid:
                tft_tft.append(await engine.get_trust(tid, pid))
        for did in def_ids:
            tft_def.append(await engine.get_trust(tid, did))
            def_tft.append(await engine.get_trust(did, tid))

    for did in def_ids:
        for tid in tft_ids:
            def_all.append(await engine.get_trust(did, tid))

    def avg(xs):
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    return {
        "round": round_num,
        "tft_tft_trust": avg(tft_tft),
        "tft_defector_trust": avg(tft_def),
        "defector_tft_trust": avg(def_tft),
        "defector_avg_trust": avg(def_all),
    }


# ── Reporting ──────────────────────────────────────

def print_report(all_metrics: list[dict]) -> dict:
    # The report uses Unicode (arrows, box drawing); make stdout tolerate it on
    # consoles that default to a non-UTF-8 codepage (e.g. Windows cp1250).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    post = [m for m in all_metrics if m["round"] > COOPERATION_ROUNDS]

    def avg(key, rows):
        vals = [r[key] for r in rows]
        return sum(vals) / len(vals) if vals else 0.0

    post_tft_tft = avg("tft_tft_trust", post)
    post_tft_def = avg("tft_defector_trust", post)
    post_def_avg = avg("defector_avg_trust", post)
    separation = post_tft_tft - post_tft_def

    print("\n" + "=" * 70)
    print("  ESS STABILITY TEST — Swarm Invasion Report")
    print("=" * 70)
    print(f"\n  Swarm: {TFT_COUNT} TFT agents + {DEFECTOR_COUNT} defectors")
    print(f"  Cooperation rounds: {COOPERATION_ROUNDS}   Invasion rounds: {INVASION_ROUNDS}")
    print(f"  Baseline trust: {BASELINE}\n")

    print(f"  📊 Post-invasion (rounds {COOPERATION_ROUNDS + 1}-{TOTAL_ROUNDS}):")
    print(f"     TFT↔TFT avg trust:   {post_tft_tft:.4f}   (built through cooperation)")
    print(f"     TFT→Defector trust:  {post_tft_def:.4f}   (collapsed)")
    print(f"     Defector→TFT trust:  {avg('defector_tft_trust', post):.4f}")
    print(f"     Defector avg trust:  {post_def_avg:.4f}")
    print(f"     Separation (TFT↔TFT − TFT→Def): {separation:.4f}\n")

    # With healing-only forgiveness, sustained cooperation BUILDS trust well above
    # baseline, while defectors are driven to ~0 — the strongest form of the proof.
    tft_stable = post_tft_tft > BASELINE + 0.1
    defector_rejected = post_tft_def < 0.1
    distinct = separation >= 0.2
    ok = tft_stable and defector_rejected and distinct

    print("  🧪 ESS Stability Test Result:")
    if ok:
        print("     ✅ PASS — TFT population is collectively stable (ESS)")
        print(f"        TFT built strong mutual trust ({post_tft_tft:.4f})")
        print(f"        Defectors driven to ~0 ({post_tft_def:.4f}) and isolated")
        print("        → Axelrod's Proposition 2 confirmed: ALL-D cannot invade TFT")
    else:
        print("     ❌ FAIL")
        print(f"        tft_stable={tft_stable} defector_rejected={defector_rejected} distinct={distinct}")

    # Key-frame table
    print("\n  📈 Round-by-round (key frames):")
    print(f"     {'Round':>6} | {'TFT-TFT':>8} | {'TFT-Def':>8} | {'Def-TFT':>8} | {'Def avg':>8}")
    print(f"     {'-' * 6}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 8}")
    key_rounds = {
        1, COOPERATION_ROUNDS // 2, COOPERATION_ROUNDS,
        COOPERATION_ROUNDS + 1, COOPERATION_ROUNDS + 3,
        COOPERATION_ROUNDS + INVASION_ROUNDS // 2, TOTAL_ROUNDS,
    }
    for m in all_metrics:
        if m["round"] in key_rounds:
            print(f"     {m['round']:>6} | {m['tft_tft_trust']:>8.4f} | "
                  f"{m['tft_defector_trust']:>8.4f} | {m['defector_tft_trust']:>8.4f} | "
                  f"{m['defector_avg_trust']:>8.4f}")
    print("\n" + "=" * 70 + "\n")

    return {
        "post_tft_tft": post_tft_tft,
        "post_tft_def": post_tft_def,
        "separation": separation,
        "pass": ok,
    }


# ── Experiment driver ──────────────────────────────

async def _make_db():
    """Build the tables from the ORM MODELS — what actually creates every real database.

    Was `executescript(schema.sql)`. But main.py states it plainly: "schema.sql is not auto-applied at
    runtime (ORM create_all is used)", and measured 2026-08-09 the two had DRIFTED on 20 of the 23
    tables they share. The one that mattered here: schema.sql declares `trust_scores.id INTEGER
    PRIMARY KEY AUTOINCREMENT`, every real database has `VARCHAR(36)`. TrustEngine._persist writes a
    uuid — correct against production, `sqlite3.IntegrityError: datatype mismatch` against
    schema.sql — so this entire ESS stability experiment could not run at all, against a database
    that exists nowhere.

    A temp FILE rather than `:memory:`: create_all needs its own connection, and a :memory: database
    is private to the connection that opened it.
    """
    import os as _os
    import tempfile
    from sqlalchemy.ext.asyncio import create_async_engine
    from agora.storage.models import Base

    fd, path = tempfile.mkstemp(suffix="-ess.db")
    _os.close(fd)
    eng = create_async_engine("sqlite+aiosqlite:///%s" % path)
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    await eng.dispose()
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    conn._ess_temp_path = path          # so the caller can clean up after closing
    return conn


async def run_experiment(db) -> list[dict]:
    engine = TrustEngine(db)

    tft_agents = [make_agent(f"tft-{i:03d}", "tft") for i in range(TFT_COUNT)]
    defectors = [make_agent(f"def-{i:03d}", "all_d") for i in range(DEFECTOR_COUNT)]
    await seed_agents(db, tft_agents + defectors)

    pair_memory: dict = {}
    all_metrics = []
    for rnd in range(1, TOTAL_ROUNDS + 1):
        # True injection: defectors are inactive until the invasion round.
        active = tft_agents if rnd <= COOPERATION_ROUNDS else tft_agents + defectors
        all_metrics.append(await run_round(engine, active, pair_memory, rnd))
    return all_metrics


# ── Pytest entry point ─────────────────────────────

if pytest is not None:
    @pytest.mark.asyncio
    async def test_ess_stability():
        """Run the swarm-invasion experiment and assert TFT is collectively stable."""
        db = await _make_db()
        try:
            all_metrics = await run_experiment(db)
            summary = print_report(all_metrics)

            assert summary["post_tft_tft"] > BASELINE + 0.1, (
                f"TFT↔TFT failed to build trust above baseline: {summary['post_tft_tft']:.4f}")
            assert summary["post_tft_def"] < 0.1, (
                f"Defectors were not rejected: {summary['post_tft_def']:.4f}")
            assert summary["separation"] >= 0.2, (
                f"TFT failed to distinguish defectors: separation {summary['separation']:.4f}")
            print("  ✅ All assertions passed — TFT is ESS")
        finally:
            await db.close()


# ── Direct execution ───────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def main():
        db = await _make_db()
        try:
            metrics = await run_experiment(db)
            summary = print_report(metrics)
            assert summary["pass"], "ESS stability criterion not met"
            print("  ✅ All assertions passed — TFT is ESS")
        finally:
            await db.close()

    asyncio.run(main())
