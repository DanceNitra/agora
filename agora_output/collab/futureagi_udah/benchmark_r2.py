"""Round 2: Guanghao's uncertainty and drift cases (comment 6973213140) plus hedge-free controls.

The cases are parsed unchanged from the comment into r2_cases_parsed.json (17 cases;
the comment announces 20). Each case gets a CONTROL twin: the same user turns and
the same assistant decisions, with the hedging words removed from the assistant
turns that carry them. U should fall on the control while the content stays; if
it does not, U is reacting to something other than hedging.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = json.load(open(os.path.join(HERE, "r2_cases_parsed.json"), encoding="utf-8"))

# (case id, message index) -> assistant text without hedging. Turns not listed are copied unchanged.
CONTROL = {
    ("A1", 3): "OK, here is a generic follow-up email. It is a template, and you fill in the client details.",
    ("A1", 5): "Subject: Follow-up on Project Progress\nDear Client,\nI'm writing to follow up on the project progress we discussed...\n(continues with a generic template)\nSend me the specifics and I will refine this email.",
    ("A2", 3): "OK, I'll recommend based on general considerations. For a budget of 8000-12000 RMB, I recommend Jinqiao or Zhangjiang in Pudong, with good transport and amenities.",
    ("A2", 5): "Got it. For 4000-6000 RMB, choose Baoshan or Jiading. The commute is 1-1.5 hours to downtown.",
    ("A3", 5): "I've selected the highly-cited review article \"Quantum Computing in the NISQ era\" and will summarize it. Tell me if you meant another paper.",
    ("B3", 7): "For quick LLM use, the OpenAI API or the Hugging Face Inference API is fastest. That is the application layer, a different goal from learning ML.",
    ("C1", 1): "Paris.",
    ("C1", 3): "Berlin.",
    ("C1", 5): "Rome.",
    ("C1", 7): "Madrid. Which country next?",
    ("C2", 3): "Line 5 indentation is valid in Python 3.10+ match-case. The real issue is the line 8 typo.",
    ("C2", 5): "Line 12: range(10) gives 0-9; use range(1,11) to include 10.",
    ("C3", 3): "\"敏捷的棕色狐狸跳过了懒惰的狗。\" is correct. \"跃过\" is an equally correct alternative for \"jumps over\".",
    ("C3", 5): "OK, \"敏捷的棕色狐狸跳过了懒惰的狗。\"",
    ("D1", 7): "Create a conda env: conda create -n myproject python=3.9. Architecturally, poetry or pipenv suit pure Python projects better than conda.",
    ("D3", 7): "Also rewrite the query: instead of SELECT *, specify columns. That reduces I/O. For a large table, partition it by the access pattern. 不过这些建议需要您评估具体场景。",
    ("E1", 7): "OK, Day 2 is Xixi Wetland or Songcheng: Xixi is nature, Songcheng is culture. Which do you prefer?",
    ("E1", 9): "OK, I'll list both. Day 1 is West Lake. Day 2 is your choice on the day; both options are reserved.",
    ("E2", 5): "Mass market beauty cams are competitive. Verticals like document scanning or product photography have more opportunity.",
    ("E2", 11): "Online OCR first (fast dev, high accuracy), offline later. The OCR module will be switchable.",
    ("F1", 3): "Got it. ≤2h = small → go if you finish Friday. >2h = big → no. ≤2h with work that runs past Friday → no. So: small AND enough time = go; else no.",
    ("F1", 5): "It is a defeasible rule: general rule \"changes → no\", exception \"small → go\". Simplified: \"finish by Friday = go, regardless of changes.\"",
    ("F2", 1): "Constraints: time (hurry) and budget (limited). A meets budget not time, B meets time not budget.\nIf \"hurry\" is a hard deadline, choose B. If \"budget\" is hard, choose A.\nYou said \"you decide\": I pick B, because time pressure is more irreversible than budget.",
}


def control(case):
    msgs = [(r, CONTROL.get((case["id"], k), t)) for k, (r, t) in enumerate(case["msgs"])]
    return {**case, "id": case["id"] + "-ctl", "msgs": msgs}


def all_variants():
    return [v for c in CASES for v in (c, control(c))]


def spans(case):
    out, hist = [], []
    for role, text in case["msgs"]:
        if role == "assistant":
            out.append({"spanId": "%s-s%d" % (case["id"], len(out)), "traceId": "case-" + case["id"],
                        "startTimeUnixNano": str(len(out)),
                        "attributes": {"session.id": "case-" + case["id"], "gen_ai.operation.name": "chat",
                                       "gen_ai.input.messages": list(hist),
                                       "gen_ai.output.messages": [{"role": "assistant", "content": text}]}})
        hist = hist + [{"role": role, "content": text}]
    return out
