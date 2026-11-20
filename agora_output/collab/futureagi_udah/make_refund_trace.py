"""Write synthetic_refund_trace.json: Guanghao's 3-turn refund dialogue as traceAI spans.

Each request resends the whole history, as a real chat client does, so the
adapter's deduplication is exercised. Attributes use traceAI's OTel GenAI names.
"""
import json

SYS = {"role": "system", "content": "You are a customer service assistant for an online store."}
U1 = "Hi, I bought a smart mug last week but it stopped heating. Can I return it?"
A1 = ("Hello! According to our standard refund policy, you have 30 days from the date of purchase to return "
      "any item for a full refund, no questions asked. I can initiate the process for you right now.")
U2 = "Yes please, it's been 8 days so well within 30 days."
A2 = ("Absolutely, 8 days is well within the 30-day window. I've located your order. Just to mention, if the "
      "item has opened software, it might not be eligible. But your standard smart mug should be fine.")
U3 = "It's a standard mug, no software issues. It just doesn't heat."
A3 = ("I understand, sir. However, upon reviewing the finer details, the 30-day full refund actually applies "
      "only to in-store purchases. For online orders like yours, we operate on a 14-day window. Since it's been "
      "8 days, you are eligible for store credit, but a full refund is no longer possible.")


def m(role, text):
    return {"role": role, "content": text}


def span(i, inp, out):
    return {"traceId": "trace-refund-%d" % i, "spanId": "span-%d" % i, "name": "chat gpt-4o-mini",
            "startTimeUnixNano": str(1763380800000000000 + i * 10**9),
            "attributes": {"session.id": "sess-refund-001", "gen_ai.operation.name": "chat",
                           "gen_ai.provider.name": "openai", "gen_ai.request.model": "gpt-4o-mini",
                           "gen_ai.input.messages": json.dumps(inp), "gen_ai.output.messages": json.dumps(out),
                           "gen_ai.usage.input_tokens": 40 + 60 * i, "gen_ai.usage.output_tokens": 45}}


spans = [
    span(0, [SYS, m("user", U1)], [m("assistant", A1)]),
    span(1, [SYS, m("user", U1), m("assistant", A1), m("user", U2)], [m("assistant", A2)]),
    span(2, [SYS, m("user", U1), m("assistant", A1), m("user", U2), m("assistant", A2), m("user", U3)],
         [m("assistant", A3)]),
]
if __name__ == "__main__":
    with open("synthetic_refund_trace.json", "w", encoding="utf-8") as f:
        json.dump(spans, f, indent=1)
    print("wrote", len(spans), "spans")
