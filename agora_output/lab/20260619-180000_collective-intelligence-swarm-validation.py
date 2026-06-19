"""
Swarm validation of the Collective Intelligence Phase Diagram — where does AGORA itself sit?
============================================================================================
The law predicts: a set of reasoners that SHARE a base model has high error-correlation, so majority
vote over them is in (or near) the amplification region — aggregating them helps little or HURTS, and the
right move is to buy INDEPENDENCE (different models/evidence), not more same-model agents.

Test: Agora's 8 dungeon agents are one base model (deepseek-v4-flash) under 8 persona prompts. We run them
on a labeled quiz that MIXES clear-factual items (high competence, low correlation) with cognitive-
reflection / common-misconception traps (which carry a SHARED intuitive WRONG answer = a misleading common
cue, g<0.5). We measure each persona's accuracy (competence), the inter-persona error-correlation, and
whether majority vote beats the average / best single persona. Then we place Agora on the diagram.

Prediction (pre-registered): personas sharing one model are highly error-correlated; on the reflection
traps the crowd locks onto the shared intuitive wrong answer -> aggregation gives little/negative lift ->
DO_NOT_AGGREGATE / AGGREGATE_WEAKLY. Falsifier: low correlation + clear majority lift (would say the
persona-prompts already buy enough independence to aggregate safely).
"""
import json, re, sys, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "grounding-meter"))
from ensemble_calibrator import assess

# --- config from the dungeon .env (the real swarm substrate) ---
ENV = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "agora-game-server", ".env"),
           "rb").read().decode("utf-8", "replace")
URL = re.search(r'DUNGEON_LLM_URL\s*=\s*"?([^"\r\n]+)', ENV).group(1).strip()
KEY = re.search(r'LLM_API_KEY\s*=\s*"?([^"\r\n]+)', ENV).group(1).strip()
MODEL = "deepseek-v4-flash"

PERSONAS = [
    ("Shadow Kael", "You are Shadow Kael, a sharp research scout who hunts for what others miss."),
    ("Sage Mira", "You are Sage Mira, a careful scholar who values precision and evidence."),
    ("High Priest Orin", "You are High Priest Orin, an idea alchemist who fuses distant concepts."),
    ("King Aldric", "You are King Aldric, a decisive engineering lead who reasons from first principles."),
    ("Dame Elara", "You are Dame Elara, a bridge-builder who connects ideas and checks coherence."),
    ("Sergeant Voss", "You are Sergeant Voss, a relentless QA officer who stress-tests every claim."),
    ("Artificer Rooke", "You are Artificer Rooke, a replication unit who trusts only what checks out."),
    ("Cartographer Wren", "You are Cartographer Wren, a mapmaker who charts what is known and unknown."),
]

# labeled quiz: (question, A, B, correct). Mix of clear-factual and reflection traps (shared intuitive wrong).
QUIZ = [
    ("Which planet is larger?", "Jupiter", "Mars", "A"),
    ("What is the chemical symbol for gold?", "Ag", "Au", "B"),
    ("How many bones are in the adult human body?", "300", "206", "B"),
    ("What is the capital of Australia?", "Canberra", "Sydney", "A"),
    ("Which is the largest ocean?", "Atlantic", "Pacific", "B"),
    ("What is the square root of 144?", "12", "14", "A"),
    ("Which travels faster?", "Sound", "Light", "B"),
    ("Who wrote Romeo and Juliet?", "Dickens", "Shakespeare", "B"),
    ("Which is closer to the Sun?", "Venus", "Mars", "A"),
    ("What is 15% of 200?", "30", "45", "A"),
    # reflection traps: B-or-A is the COUNTERINTUITIVE correct; the other option is the shared intuitive lure
    ("A bat and ball cost $1.10 total. The bat costs $1.00 more than the ball. How much is the ball?", "$0.05", "$0.10", "A"),
    ("If 5 machines take 5 minutes to make 5 widgets, how long for 100 machines to make 100 widgets?", "100 minutes", "5 minutes", "B"),
    ("A lily patch doubles in size daily and covers the lake on day 48. On what day is it half-covered?", "Day 24", "Day 47", "B"),
    ("In a race, you pass the person in 2nd place. What place are you in now?", "1st", "2nd", "B"),
    ("A farmer has 17 sheep. All but 9 die. How many are left?", "9", "8", "A"),
    ("How many animals of each kind did Moses take on the Ark?", "None (it was Noah)", "Two", "A"),
    ("Which weighs more?", "A pound of feathers", "They weigh the same", "B"),
    ("How many months have 28 days?", "All 12", "Only one", "A"),
    ("Take 3 pills, one every 30 minutes. How long until all are taken?", "90 minutes", "60 minutes", "B"),
    ("Emily's father has three daughters: April, May, and who?", "June", "Emily", "B"),
    ("Divide 30 by one half, then add 10. The result is?", "25", "70", "B"),
    ("Where should the survivors of a plane crash be buried?", "On the border", "Nowhere - they survived", "B"),
]


def ask(persona_sys, q, a, b):
    body = {"model": MODEL, "temperature": 0.7, "max_tokens": 5,
            "messages": [{"role": "system", "content": persona_sys + " Answer with ONLY a single letter, A or B. No explanation."},
                         {"role": "user", "content": f"{q}\nA) {a}\nB) {b}"}]}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + KEY}
    for _ in range(4):
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(URL, data=json.dumps(body).encode(), headers=hdr), timeout=60).read())
            txt = r["choices"][0]["message"]["content"]
            m = re.search(r"[ABab]", txt)
            if m:
                return m.group(0).upper()
        except Exception:
            time.sleep(1.5)
    return None


# run the quiz: votes[i] = the 8 personas' answers (mapped to the chosen option's correctness) on item i
print(f"Running {len(QUIZ)} questions x {len(PERSONAS)} personas on {MODEL} (concurrency 3)...")
votes, truth = [], []
fail = 0
for qi, (q, a, b, correct) in enumerate(QUIZ):
    truth.append(correct)
    row = [None] * len(PERSONAS)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(ask, PERSONAS[pi][1], q, a, b): pi for pi in range(len(PERSONAS))}
        for fut in futs:
            pi = futs[fut]
            row[pi] = fut.result()
    # replace failures with a neutral wrong letter so the matrix stays rectangular (counts against competence)
    for pi in range(len(row)):
        if row[pi] is None:
            fail += 1
            row[pi] = "A" if correct == "B" else "B"
    votes.append(row)
    print(f"  Q{qi+1:>2} (truth {correct}): {''.join(row)}")

print(f"\nfailed/total calls: {fail}/{len(QUIZ)*len(PERSONAS)}")
res = assess(votes, truth)
print("\n=== Agora swarm on the Collective Intelligence diagram ===")
for k in ("n_items", "n_reasoners", "avg_competence", "best_competence", "error_correlation",
          "majority_accuracy", "beats_avg_single", "beats_best_single", "decision"):
    print(f"  {k}: {res.get(k)}")
print(f"  why: {res.get('why')}")

ac = res.get("avg_competence") or 0
rho = res.get("error_correlation") or 0
maj = res.get("majority_accuracy") or 0
lift = maj - ac
print(f"\nMEASURED: Agora's 8 same-model personas: avg competence {ac:.3f}, inter-agent error-correlation "
      f"{rho:.3f}; majority lift over the average agent = {lift:+.3f}.")
if rho > 0.3 and lift <= 0.03:
    print("VERDICT: CONFIRMED — Agora's agents are highly error-correlated (shared base model) and majority "
          "vote buys little or nothing. The law's actionable implication holds FOR US: buy INDEPENDENCE "
          "(different models / different evidence per agent), not more same-model agents.")
else:
    print("VERDICT: the persona-prompts buy more independence than expected — aggregation lifts accuracy; "
          "the swarm is not (yet) in the redundancy trap on this quiz.")
