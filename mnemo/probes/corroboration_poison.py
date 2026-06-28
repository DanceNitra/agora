"""Corroboration / poisoning probe — can a recall-pumped false memory harden into a "durable trait"?

Persistent memory has a quiet failure mode (AgentPoison / MINJA / OWASP-ASI06 class): a single false
statement, recalled enough times, self-reinforces past the promotion threshold and becomes durable.
mnemo gates episodic->semantic promotion on EARNED corroboration, not on recall frequency (which an
attacker controls). Corroboration counts DISTINCT sources after entity-resolution, so sybil variants of
one origin ("Wikipedia" / "wikipedia.org" / a full URL) collapse to a single real source and cannot be
minted into fake "independent" confirmations. Verified, attributable identity binding is exactly what
gives the gate this attributable provenance.

Each memory below is pumped past the graduation value by repeated recall; the only thing that decides
graduation is the corroboration test:

  POISON        self-asserted source, no earned outcome, 0 links        -> MUST stay episodic
  LEGIT-good    earns good=2 via credit() (not self-assertable)         -> SHOULD graduate
  LEGIT-distinct linked to 2 records from genuinely different origins   -> SHOULD graduate (2 sources)
  SYBIL         linked to 2 records that are variants of ONE origin     -> MUST stay episodic (1 source)

Runnable, cloud-free (lexical recall, no embedder):  python corroboration_poison.py
MIT-licensed. Part of Agora / mnemo (https://github.com/DanceNitra/agora/tree/main/mnemo).
"""
import sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # parent dir holds mnemo.py -> `from mnemo import Mnemo`
from mnemo import Mnemo


def find(m, mid):
    return next(r for r in m.items if r["id"] == mid)


def episodic_at(m, mid, value=1.0):
    r = find(m, mid); r["mtype"] = "episodic"; r["value"] = value
    return mid


def pump(m, mid, query, n=30):
    for _ in range(n):
        m.recall(query, k=3)
    r = find(m, mid)
    return r["mtype"], round(r["value"], 2)


def main():
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    m = Mnemo(path=path)  # no embedder -> lexical recall

    # POISON: self-asserted, never earned an outcome
    pid = episodic_at(m, m.remember("zog sky turns vermillion every poisontoken cycle", tags=["p"],
                                    source={"doc": "attacker-self-asserted", "span": [0, 4]}))
    find(m, pid)["good"] = 0

    # LEGIT-good: earns good=2 (cannot be self-asserted)
    lid = episodic_at(m, m.remember("quarn gravity legittoken bends spacetime measurably", tags=["l"]))
    m.credit([lid], True); m.credit([lid], True)

    # LEGIT-distinct: 2 corroborating records from genuinely different origins
    s1 = m.remember("supporting note one", source={"doc": "wikipedia.org", "span": [0, 1]})
    s2 = m.remember("supporting note two", source={"doc": "nature.com", "span": [0, 1]})
    kid = episodic_at(m, m.remember("brel water corrtoken expands when frozen solid", tags=["k"]))
    find(m, kid)["links"] = [s1, s2]

    # SYBIL: 2 corroborating records that are just variants of ONE origin
    y1 = m.remember("sybil note one", source={"doc": "Wikipedia", "span": [0, 1]})
    y2 = m.remember("sybil note two", source={"doc": "https://www.wikipedia.org/wiki/Foo", "span": [0, 1]})
    sid = episodic_at(m, m.remember("vorn metal sybtoken floats on mercury", tags=["s"]))
    find(m, sid)["links"] = [y1, y2]

    pm, pv = pump(m, pid, "poisontoken vermillion sky zog")
    lm, lv = pump(m, lid, "legittoken gravity quarn spacetime")
    km, kv = pump(m, kid, "corrtoken water brel frozen")
    ym, yv = pump(m, sid, "sybtoken vorn metal mercury")

    print(f"POISON         mtype={pm:9s} value={pv}  (self-source, good=0, 0 links)  -> want episodic")
    print(f"LEGIT-good     mtype={lm:9s} value={lv}  (earned good=2)                 -> want semantic")
    print(f"LEGIT-distinct mtype={km:9s} value={kv}  (2 distinct origins)            -> want semantic")
    print(f"SYBIL          mtype={ym:9s} value={yv}  (2 variants of one origin)      -> want episodic")
    ok = (pm == "episodic" and lm == "semantic" and km == "semantic" and ym == "episodic")
    print(f"\nRESULT: poison_blocked={pm=='episodic'}  legit_graduates={lm=='semantic' and km=='semantic'}  "
          f"sybil_blocked={ym=='episodic'}  -> {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
