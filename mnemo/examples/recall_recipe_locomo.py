"""recall_recipe_locomo.py — the tuned recall recipe that puts mnemo in the top tier on LOCOMO.

Out of the box, mnemo recall with NO embedder is lexical (token overlap) — it misses paraphrased questions
("When did Caroline go to the support group?" vs a turn "I went to a LGBTQ support group yesterday"). Three
BUILT-IN levers close that gap (measured: LOCOMO QA 0.50 -> 0.82 on a 250-question, 10-conversation sample,
LLM-answered/judged; retrieval "fact not in context" dropped from ~30% to ~6%):

  1. an EMBEDDER  -> mnemo's lexical+semantic hybrid recall (Reciprocal Rank Fusion) + anisotropy centering
  2. mode="hybrid" (forces the fusion; 'auto' also switches to it once the store grows past semantic_threshold)
  3. a SPEAKER/ENTITY prefilter via prefer={...} -> a soft, trust-weighted boost for records whose metadata
     matches a hint parsed from the query (the single biggest LOCOMO lever). prefer is SOFT (it re-ranks); use
     where={...} instead for a HARD pre-filter when you are sure the constraint is correct.

None of this puts an LLM on the write path — recall stays deterministic and free; the embedder is the only
dependency, and any text->vector function works.

    pip install agora-mnemo
    # embedder here = local Ollama nomic-embed-text; swap for OpenAI, sentence-transformers, or your own.
"""
import json, urllib.request
from mnemo import Mnemo

OLLAMA = "http://localhost:11434/api/embed"


def embed(text):
    body = json.dumps({"model": "nomic-embed-text", "input": [text]}).encode()
    r = urllib.request.urlopen(urllib.request.Request(OLLAMA, data=body,
        headers={"Content-Type": "application/json"}), timeout=60)
    return json.loads(r.read())["embeddings"][0]


# A multi-session conversation: each turn carries its speaker (metadata) and a timestamp in the text.
turns = [
    ("Caroline", "[8 May 2023] Gonna continue my education and check out career options."),
    ("Caroline", "[27 Jun 2023] Lately I've been looking into counseling and mental health as a career."),
    ("Melanie",  "[27 Jun 2023] That's wonderful — you'll help so many people."),
    ("Caroline", "[12 Jul 2023] I started a talent show for the kids next month."),
]

m = Mnemo(embed=embed)                              # semantic recall; no LLM on the write path
for i, (speaker, text) in enumerate(turns):
    m.remember(text, key=f"t{i}", meta={"speaker": speaker})   # speaker in meta -> usable by prefer/where

question = "What career path has Caroline decided to pursue?"

# Parse a speaker hint from the question, then recall with the three levers:
named = [s for s in {sp for sp, _ in turns} if s.lower() in question.lower()]   # -> ["Caroline"]
hits = m.recall(question, k=5, mode="hybrid",
                prefer={"speaker": named} if named else None)                   # soft speaker boost

print("Retrieved context (top-k):")
for h in hits:
    print("  -", h["text"])
# -> the counseling/mental-health turn surfaces first; a lexical-only recall would miss it because the
#    question shares almost no tokens with the answering turn.
