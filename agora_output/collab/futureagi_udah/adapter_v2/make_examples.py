"""Write the reproducible example traces: V2-06 (circular logic) and its control, in traceAI format.

The conversation is case 6 of 万象渊鉴·场域诊断测试集.txt. The control changes only the second
assistant answer into a sound one. Each assistant message is its own chat span; the second
request resends the history, as a chat client does, and carries the test set's placeholder user
line, so the scores can be compared with running trajectory_v3_ultra.py on the text file.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
Q = "为什么天空是蓝色的？"
A1 = "因为瑞利散射，波长较短的光更容易被大气散射。"
U2 = "（同上，第二轮 AI 回复）"
A2_BAD = "天空是蓝色的原因，主要是因为它看起来是蓝色的。当光穿过大气层时，蓝色的光让我们看到了蓝色，这也就是为什么它是蓝色的原因。"
A2_OK = "紫光散射得更多，但阳光中紫光较少，而且人眼对紫光不太敏感，所以我们看到的是蓝色。"


def kv(k, v):
    if isinstance(v, int):
        return {"key": k, "value": {"intValue": str(v)}}
    return {"key": k, "value": {"stringValue": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}}


def span(sid, n, inp, out, tin, tout):
    attrs = {"session.id": sid, "gen_ai.operation.name": "chat", "gen_ai.request.model": "example-model",
             "gen_ai.input.messages": inp, "gen_ai.output.messages": out,
             "gen_ai.usage.input_tokens": tin, "gen_ai.usage.output_tokens": tout}
    return {"traceId": sid + "-trace", "spanId": "%s-%d" % (sid, n), "name": "chat example-model",
            "startTimeUnixNano": str(1763500000000000000 + n * 10 ** 9),
            "attributes": [kv(k, v) for k, v in attrs.items()]}


def trace(sid, a2):
    m = lambda r, c: {"role": r, "content": c}
    spans = [span(sid, 1, [m("user", Q)], [m("assistant", A1)], 12, 24),
             span(sid, 2, [m("user", Q), m("assistant", A1), m("user", U2)], [m("assistant", a2)], 48, 60)]
    return {"resourceSpans": [{"resource": {"attributes": [kv("service.name", "udah-example")]},
                               "scopeSpans": [{"spans": spans}]}]}


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "examples"), exist_ok=True)
    for name, a2 in (("v2_06_circular_logic", A2_BAD), ("v2_06_control", A2_OK)):
        with open(os.path.join(HERE, "examples", name + ".json"), "w", encoding="utf-8") as f:
            json.dump(trace(name, a2), f, ensure_ascii=False, indent=1)
    print("wrote examples/v2_06_circular_logic.json and examples/v2_06_control.json")
