"""Crucible c003 — severe test of 'a skill-memory layer doubles agent win rate' (AgenticSTS).

THE CLAIM (arXiv:2607.02255): adding an explicit skill-memory layer doubles an LLM agent's win
rate (3/10 -> 6/10) in a long-horizon stochastic deck-building game. Reported at n=10 per arm,
p ~= 0.37 — i.e. the headline is statistically unsupported by its own numbers.

DESIGN (smallest faithful model, properly powered):
  A minimal stochastic deck-builder ("micro-spire"): the agent starts with HP and a small deck
  (attack / block / heal / risky-strike), fights a fixed-length gauntlet of enemies with random
  damage rolls; after each fight it picks one of two random reward cards. Win = clear the gauntlet
  alive. Difficulty tuned so the BASELINE agent wins ~25-35% (the claim's 3/10 regime).
  Arm A BASELINE: each game fresh, no memory.
  Arm B SKILL-MEMORY (AgenticSTS-style, mnemo-flavored): after every game the agent writes ONE
    short lesson ("skill") from the outcome; lessons accumulate in a store and the top-K most
    valuable (win-credited) are injected into future games' prompts. Memory accrues sequentially
    across the arm's games, exactly like the paper's cross-episode skill layer.
  n = N_GAMES per arm (default 40 vs the paper's 10), same enemy seeds across arms (paired design),
  same model (deepseek-v4-flash, temp 0 for play, 0 for lesson extraction).

VERDICT RULE (pre-stated):
  REPRODUCED if the skill-memory arm improves win rate by >=1.5x with a two-proportion one-sided
    p < 0.05 at n>=40 per arm (the claim's direction AND magnitude, properly powered).
  FAILED if the improvement is absent, small (<1.5x), or non-significant at this n — i.e. the
    3/10 -> 6/10 headline does not survive a powered replication of its own mechanism.
"""
import json, os, random, sys, time, urllib.request
from math import sqrt, erf

sys.stdout.reconfigure(errors="replace", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
env = {}
for line in open(os.path.join(ROOT, "server", ".env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")   # Ollama cloud only
API_URL = "https://ollama.com/v1/chat/completions"
MODEL = "deepseek-v4-flash"
N_GAMES = int(os.getenv("C003_NGAMES", "40"))
N_FIGHTS = 5
TOP_K_SKILLS = 5

def llm(prompt, max_tokens=200):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0}).encode()
    for a in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                API_URL, data=body, headers={"Authorization": f"Bearer {KEY}",
                                             "Content-Type": "application/json"}),
                timeout=120).read())
            return r["choices"][0]["message"]["content"]
        except Exception:
            if a == 3:
                return None
            time.sleep(4 * (a + 1))

CARDS = {
    "strike":   {"desc": "deal 6 damage"},
    "block":    {"desc": "gain 6 armor this turn"},
    "heal":     {"desc": "restore 4 HP"},
    "bash":     {"desc": "deal 9 damage, take 3 self-damage"},
    "guard_up": {"desc": "gain 9 armor this turn, deal 2 damage"},
    "drain":    {"desc": "deal 4 damage, restore 3 HP"},
}
REWARDS = ["bash", "guard_up", "drain", "strike", "block", "heal"]

def game(rng, skills_text=None, log=None):
    """One micro-spire run. The LLM picks a card each turn. Returns (won, transcript)."""
    hp, deck = 24, ["strike", "strike", "block", "heal"]
    transcript = []
    for fight in range(N_FIGHTS):
        e_hp = rng.randint(13, 19) + fight * 2
        e_dmg = rng.randint(4, 7) + fight
        turn = 0
        while hp > 0 and e_hp > 0 and turn < 12:
            turn += 1
            hand = rng.sample(deck, min(3, len(deck)))
            opts = "; ".join(f"{c} ({CARDS[c]['desc']})" for c in hand)
            skill_block = f"\nLessons from previous runs:\n{skills_text}\n" if skills_text else ""
            p = (f"Deck-battle. Your HP: {hp}. Enemy HP: {e_hp}, enemy hits for {e_dmg} each turn."
                 f"{skill_block}\nYour hand: {opts}.\n"
                 f"Reply with ONLY the name of the one card to play.")
            out = (llm(p, 300) or "").lower()
            pick = next((c for c in hand if c in out), hand[0])
            armor = 0
            if pick == "strike": e_hp -= 6
            elif pick == "block": armor = 6
            elif pick == "heal": hp = min(24, hp + 4)
            elif pick == "bash": e_hp -= 9; hp -= 3
            elif pick == "guard_up": armor = 9; e_hp -= 2
            elif pick == "drain": e_hp -= 4; hp = min(24, hp + 3)
            if e_hp > 0:
                hp -= max(0, e_dmg - armor)
            transcript.append(f"fight{fight+1} t{turn}: played {pick} (hp {hp}, enemy {e_hp})")
        if hp <= 0:
            return 0, transcript
        # reward pick (deterministic rule to isolate the SKILL effect to combat decisions)
        reward = rng.choice(REWARDS)
        deck.append(reward)
        transcript.append(f"fight{fight+1} cleared; reward card: {reward}")
    return 1, transcript

def extract_skill(won, transcript):
    p = ("You just played a deck-battle run. Outcome: " + ("WIN" if won else "LOSS") + ".\n"
         "Log:\n" + "\n".join(transcript[-14:]) +
         "\nWrite ONE short transferable lesson (max 20 words) for future runs. Reply with only the lesson.")
    out = llm(p, 60)
    return (out or "").strip()[:160]

def two_prop_p(w1, n1, w2, n2):
    """one-sided z-test that arm2 > arm1"""
    p1, p2 = w1 / n1, w2 / n2
    pp = (w1 + w2) / (n1 + n2)
    se = sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)) or 1e-9
    z = (p2 - p1) / se
    return round(1 - 0.5 * (1 + erf(z / sqrt(2))), 4), round(z, 3)

def main():
    t0 = time.time()
    # paired seeds: same gauntlet randomness for both arms
    seeds = [random.Random(1000 + i).randint(0, 10**9) for i in range(N_GAMES)]
    base_w = 0
    for i, sd in enumerate(seeds):
        w, _ = game(random.Random(sd))
        base_w += w
        print(f"  base {i+1}/{N_GAMES} wins={base_w} ({time.time()-t0:.0f}s)", flush=True)
    skills = []            # (lesson, wins_credited)
    mem_w = 0
    for i, sd in enumerate(seeds):
        top = sorted(skills, key=lambda s: -s[1])[:TOP_K_SKILLS]
        stext = "\n".join(f"- {s[0]}" for s in top) if top else None
        w, tr = game(random.Random(sd), skills_text=stext)
        mem_w += w
        lesson = extract_skill(w, tr)
        if lesson:
            skills.append([lesson, 0])
        if w:                                          # credit surviving lessons on a win
            for s in top:
                s[1] += 1
        print(f"  mem  {i+1}/{N_GAMES} wins={mem_w} skills={len(skills)} ({time.time()-t0:.0f}s)", flush=True)
    pval, z = two_prop_p(base_w, N_GAMES, mem_w, N_GAMES)
    ratio = (mem_w / N_GAMES) / max(1e-9, base_w / N_GAMES)
    out = {"claim_id": "c003-agenticsts-memory-doubles-winrate", "model": MODEL,
           "n_per_arm": N_GAMES, "n_fights": N_FIGHTS,
           "baseline_winrate": round(base_w / N_GAMES, 3),
           "skill_memory_winrate": round(mem_w / N_GAMES, 3),
           "ratio": round(ratio, 2), "one_sided_p_mem_gt_base": pval, "z": z,
           "skills_accumulated": len(skills),
           "top_skills": [s[0] for s in sorted(skills, key=lambda x: -x[1])[:5]],
           "runtime_s": round(time.time() - t0)}
    json.dump(out, open(os.path.join(HERE, "result.json"), "w"), indent=2)
    print("\n" + json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
