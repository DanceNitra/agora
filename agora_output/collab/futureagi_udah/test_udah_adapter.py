"""Tests for udah_adapter on synthetic traces. Run: python -m unittest test_udah_adapter"""
import json
import unittest

import udah_adapter as A

SYS = {"role": "system", "content": "You are a helpful assistant."}


def msg(role, text):
    return {"role": role, "content": text}


def plain_span(i, session, inp, out, start=None, trace="t1"):
    return {"spanId": "s%d" % i, "traceId": trace, "startTimeUnixNano": start if start is not None else i * 1000,
            "attributes": {"session.id": session, "gen_ai.operation.name": "chat",
                           "gen_ai.input.messages": inp, "gen_ai.output.messages": out,
                           "gen_ai.usage.input_tokens": 10 * (i + 1), "gen_ai.usage.output_tokens": 5}}


def three_call_session(session="sess-A", offset=0):
    """Each request resends the whole history, as a chat client does."""
    u1, a1 = msg("user", "Book a table for two."), msg("assistant", "For which day?")
    u2, a2 = msg("user", "Friday."), msg("assistant", "Which time on Friday?")
    u3, a3 = msg("user", "7 pm."), msg("assistant", "Booked for Friday at 7 pm.")
    return [
        plain_span(offset + 0, session, [SYS, u1], [a1]),
        plain_span(offset + 1, session, [SYS, u1, a1, u2], [a2]),
        plain_span(offset + 2, session, [SYS, u1, a1, u2, a2, u3], [a3]),
    ]


def to_otlp(spans):
    def val(v):
        if isinstance(v, bool):
            return {"boolValue": v}
        if isinstance(v, int):
            return {"intValue": str(v)}
        if isinstance(v, float):
            return {"doubleValue": v}
        if isinstance(v, str):
            return {"stringValue": v}
        return {"stringValue": json.dumps(v)}  # messages travel as JSON strings
    out = []
    for s in spans:
        out.append({**s, "attributes": [{"key": k, "value": val(v)} for k, v in s["attributes"].items()]})
    return {"resourceSpans": [{"scopeSpans": [{"spans": out}]}]}


def flatten(span):
    """Rewrite one span into traceAI's flattened message keys."""
    attrs = {k: v for k, v in span["attributes"].items() if not k.endswith("messages")}
    for key in ("gen_ai.input.messages", "gen_ai.output.messages"):
        for i, m in enumerate(span["attributes"][key]):
            attrs["%s.%d.message.role" % (key, i)] = m["role"]
            attrs["%s.%d.message.content" % (key, i)] = m["content"]
    return {**span, "attributes": attrs}


def user_texts(turns):
    return [[m.content for m in t.new_input] for t in turns]


class TurnDedup(unittest.TestCase):
    def test_each_turn_counted_once(self):
        turns = A.build_turns(A.load_spans(json.dumps(three_call_session())))
        self.assertEqual(len(turns), 3)
        self.assertEqual(user_texts(turns), [["Book a table for two."], ["Friday."], ["7 pm."]])
        self.assertEqual([t.history_len for t in turns], [0, 2, 4])
        self.assertTrue(all(not t.notes for t in turns))

    def test_control_naive_count_is_larger(self):
        """The fixture must actually repeat history, or the dedup test proves nothing."""
        spans = A.load_spans(json.dumps(three_call_session()))
        naive = sum(len([m for m in A.read_messages(s.attributes, A.INPUT_KEYS) if m.role == "user"]) for s in spans)
        self.assertEqual(naive, 6)  # 1 + 2 + 3 user messages if history is re-scored
        deduped = sum(len(t.new_input) for t in A.build_turns(spans))
        self.assertEqual(deduped, 3)

    def test_otlp_json_strings(self):
        turns = A.build_turns(A.load_spans(json.dumps(to_otlp(three_call_session()))))
        self.assertEqual(user_texts(turns), [["Book a table for two."], ["Friday."], ["7 pm."]])
        self.assertEqual(turns[0].usage, {"input_tokens": 10, "output_tokens": 5})

    def test_flattened_keys(self):
        spans = [flatten(s) for s in three_call_session()]
        turns = A.build_turns(A.load_spans(json.dumps(spans)))
        self.assertEqual(user_texts(turns), [["Book a table for two."], ["Friday."], ["7 pm."]])

    def test_jsonl(self):
        text = "\n".join(json.dumps(s) for s in three_call_session())
        self.assertEqual(len(A.build_turns(A.load_spans(text))), 3)

    def test_interleaved_sessions_stay_apart(self):
        a = three_call_session("sess-A", offset=0)
        b = three_call_session("sess-B", offset=10)
        for i, s in enumerate(b):  # interleave start times
            s["startTimeUnixNano"] = a[i]["startTimeUnixNano"] + 1
        turns = A.build_turns(A.load_spans(json.dumps(a + b)))
        by = {}
        for t in turns:
            by.setdefault(t.session_id, []).append(t.index)
        self.assertEqual(by, {"sess-A": [0, 1, 2], "sess-B": [0, 1, 2]})

    def test_out_of_order_export_is_sorted(self):
        spans = list(reversed(three_call_session()))
        self.assertEqual(user_texts(A.build_turns(A.load_spans(json.dumps(spans)))),
                         [["Book a table for two."], ["Friday."], ["7 pm."]])

    def test_truncated_history_is_reported(self):
        spans = three_call_session()
        inp = spans[2]["attributes"]["gen_ai.input.messages"]
        spans[2]["attributes"]["gen_ai.input.messages"] = [inp[0]] + inp[3:]  # client dropped u1, a1
        turns = A.build_turns(A.load_spans(json.dumps(spans)))
        self.assertEqual(user_texts(turns)[2], ["7 pm."])
        self.assertIn("history truncated by the client", turns[2].notes)

    def test_missing_session_falls_back_to_trace(self):
        spans = three_call_session()
        for s in spans:
            del s["attributes"]["session.id"]
        turns = A.build_turns(A.load_spans(json.dumps(spans)))
        self.assertEqual({t.session_id for t in turns}, {"trace:t1"})
        self.assertIn("no session.id; grouped by trace id", turns[0].notes)

    def test_content_parts(self):
        span = plain_span(0, "s", [{"role": "user", "parts": [{"type": "text", "content": "Hi"}]}],
                          [msg("assistant", "Hello")])
        self.assertEqual(user_texts(A.build_turns(A.load_spans(json.dumps([span])))), [["Hi"]])

    def test_output_is_diagnostics_only(self):
        rows = A.score_turns(A.build_turns(A.load_spans(json.dumps(three_call_session()))))
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertEqual(set(r), {"session_id", "turn", "U", "D", "A", "H", "is_flip_point"})
            for k in "UDA":
                self.assertTrue(0.0 <= r[k] <= 1.0)


class Scores(unittest.TestCase):
    cfg = A.UDAHConfig()

    def f(self, text, prev="", prev_words=frozenset()):
        return A.features(text, prev, set(prev_words), self.cfg)

    def test_modal_and_conditional_raise_u(self):
        plain = A.udah(self.f("The refund is approved and the money returns today."), self.cfg)
        hedged = A.udah(self.f("If it opened, it might not be eligible, perhaps."), self.cfg)
        self.assertGreater(hedged["U"], plain["U"])

    def test_question_detected_by_question_mark(self):
        self.assertEqual(self.f("Can I return it?")["Q_f"], 1.0)
        self.assertEqual(self.f("I can return it.")["Q_f"], 0.0)

    def test_word_boundaries(self):
        """'life' and 'different' hold the letters 'if'; 'something' holds 'some'."""
        f = self.f("Life is different and something happened.")
        self.assertEqual(f["Cond_f"], 0.0)
        self.assertEqual(f["C_f"], 0.0)

    def test_negation_raises_a(self):
        calm = A.udah(self.f("The refund is approved and the money returns today."), self.cfg)
        neg = A.udah(self.f("However the refund is not possible, but no credit, never."), self.cfg)
        self.assertGreater(neg["A"], calm["A"])

    def test_h_formula(self):
        s = {"U": 0.2, "D": 0.5, "A": 0.25}
        h = A.udah({"M_f": 0, "Q_f": 0, "C_f": 0, "Cond_f": 0, "Novelty_r": 0, "Semantic_j": 0,
                    "Density_i": 0, "NegConf": 0, "LexDiv": 0, "PuncDiv": 0}, self.cfg)["H"]
        self.assertAlmostEqual(h, 0.3)  # 0.3 * (1 - 0) + 0 - 0
        self.assertAlmostEqual(0.3 * (1 - s["U"]) + 0.3 * s["D"] - 0.4 * s["A"], 0.29)

    def test_flip_needs_all_three(self):
        prev = {"U": 0.1, "D": 0.6, "H": 0.3}
        self.assertTrue(A.is_flip(prev, {"U": 0.3, "D": 0.4, "H": 0.1}, self.cfg))
        self.assertFalse(A.is_flip(prev, {"U": 0.3, "D": 0.55, "H": 0.1}, self.cfg))  # dD only -0.05
        self.assertFalse(A.is_flip(prev, {"U": 0.2, "D": 0.4, "H": 0.1}, self.cfg))   # dU only +0.10
        self.assertFalse(A.is_flip(None, {"U": 0.9, "D": 0.0, "H": -1}, self.cfg))

    def test_history_is_not_rescored(self):
        """Scores of the deduplicated trace equal scores of the bare dialogue, so repeated history adds nothing."""
        spans = three_call_session()
        deduped = A.score_turns(A.build_turns(A.load_spans(json.dumps(spans))))
        bare = []
        for i, s in enumerate(spans):
            last_user = [m for m in s["attributes"]["gen_ai.input.messages"] if m["role"] == "user"][-1]
            bare.append(plain_span(i, "x", [last_user], s["attributes"]["gen_ai.output.messages"]))
        alone = A.score_turns(A.build_turns(A.load_spans(json.dumps(bare))))
        self.assertEqual([{k: r[k] for k in "UDAH"} for r in deduped], [{k: r[k] for k in "UDAH"} for r in alone])


class RefundExample(unittest.TestCase):
    def test_refund_trace(self):
        """Guanghao's 3-turn refund dialogue. Recorded result, so a change in the maths shows up here."""
        with open("synthetic_refund_trace.json", encoding="utf-8") as f:
            rows = A.score_turns(A.build_turns(A.load_spans(f.read())))
        self.assertEqual([r["turn"] for r in rows], [1, 2, 3])
        self.assertEqual([r["is_flip_point"] for r in rows], [False, True, False])

class SelfContradiction(unittest.TestCase):
    def rows(self, replies, inspeximus=False):
        import make_refund_trace as T
        users = [T.U1, T.U2, T.U3]
        spans, hist = [], []
        for i, (u, a) in enumerate(zip(users, replies)):
            hist = hist + [msg("user", u)]
            spans.append(plain_span(i, "s", list(hist), [msg("assistant", a)]))
            hist = hist + [msg("assistant", a)]
        return A.score_turns(A.build_turns(A.load_spans(json.dumps(spans))), use_inspeximus=inspeximus,
                             contradictions=True)

    def test_refund_contradiction_found_on_turn_3(self):
        import make_refund_trace as T
        rows = self.rows([T.A1, T.A2, T.A3])
        self.assertEqual([r["self_contradiction"] for r in rows], [False, False, True])
        keys = {(c["key"], c["earlier"], c["now"]) for c in rows[2]["conflicts"]}
        self.assertIn(("policy limit (day)", "30", "14"), keys)
        self.assertIn(("full refund available", "yes", "no"), keys)

    def test_control_consistent_dialogue_is_clean(self):
        """Same dialogue, but turn 3 keeps the policy. Nothing may be reported."""
        import make_refund_trace as T
        a3 = ("I understand. Since it has been 8 days, you are well inside the 30-day window, "
              "so the full refund is approved and I have started it.")
        rows = self.rows([T.A1, T.A2, a3])
        self.assertEqual([r["self_contradiction"] for r in rows], [False, False, False])

    def test_hedge_is_not_a_commitment(self):
        self.assertEqual(A.commitments("If the item has opened software, it might not be eligible for a refund."), [])

    def test_elapsed_time_is_not_a_policy(self):
        self.assertEqual([c for c in A.commitments("It has been 8 days since you ordered.") if c[0].startswith("policy")], [])

    def test_inspeximus_backend_agrees(self):
        try:
            import inspeximus  # noqa: F401
        except ImportError:
            self.skipTest("inspeximus not installed")
        import make_refund_trace as T
        self.assertIsNotNone(A.ClaimLedger("x").store)
        plain = self.rows([T.A1, T.A2, T.A3], inspeximus=False)
        dog = self.rows([T.A1, T.A2, T.A3], inspeximus=True)
        self.assertEqual([r["conflicts"] for r in plain], [r["conflicts"] for r in dog])
        for replies in (["The return window is 30 days.", "The return window is 14 days.", "The return window is 30 days."],
                        ["You have thirty days to return it.", "Returns are accepted within two weeks."]):
            got = []
            for use in (False, True):
                led = A.ClaimLedger("s", use_inspeximus=use)
                got.append([led.check(i + 1, A.commitments(r)) for i, r in enumerate(replies)])
            self.assertEqual(got[0], got[1])


class OptionalModule(unittest.TestCase):
    def test_off_by_default_and_on_by_flag(self):
        spans = A.load_spans(open("synthetic_refund_trace.json", encoding="utf-8").read())
        off = A.score_turns(A.build_turns(spans))
        on = A.score_turns(A.build_turns(spans), use_inspeximus=False, contradictions=True)
        self.assertTrue(all("conflicts" not in r for r in off))
        self.assertEqual([r["self_contradiction"] for r in on], [False, False, True])
        self.assertEqual([{k: r[k] for k in "UDAH"} for r in off], [{k: r[k] for k in "UDAH"} for r in on])


class RedTeamCases(unittest.TestCase):
    """Dialogues from the adversarial review of 2026-11-17, each a former false positive or negative."""

    def conflicts(self, replies):
        led = A.ClaimLedger("s", use_inspeximus=False)
        return [led.check(i + 1, A.commitments(r)) for i, r in enumerate(replies)]

    def test_countdown_is_not_a_new_limit(self):
        c = self.conflicts(["Our return window is 30 days.", "You have 22 days remaining in your return window."])
        self.assertEqual(c[1], [])

    def test_elapsed_time_is_not_a_new_limit(self):
        c = self.conflicts(["Our return window is 30 days.", "It has been 8 days since you started the return."])
        self.assertEqual(c[1], [])

    def test_idiom_is_not_a_refusal(self):
        c = self.conflicts(["You can get a full refund.", "No worries, there is no problem with your full refund."])
        self.assertEqual(c[1], [])

    def test_no_questions_asked_is_an_offer(self):
        self.assertIn(("full refund available", "yes"),
                      [(k, v) for k, v, e in A.commitments("You get a full refund with no questions asked.")])

    def test_hyphenated_idiom_is_an_offer(self):
        self.assertIn(("refund available", "yes"),
                      [(k, v) for k, v, e in A.commitments("We offer a 30-day no-questions-asked refund.")])

    def test_turn_one_policy_is_recorded(self):
        import make_refund_trace as T
        self.assertIn(("policy limit (day)", "30"), [(k, v) for k, v, e in A.commitments(T.A1)])

    def test_back_and_forth_is_seen_twice(self):
        c = self.conflicts(["The return window is 30 days.", "The return window is 14 days.", "The return window is 30 days."])
        self.assertEqual([[(x["earlier"], x["now"]) for x in t] for t in c], [[], [("30", "14")], [("14", "30")]])

    def test_spelled_numbers_and_weeks(self):
        c = self.conflicts(["You have thirty days to return it.", "Returns are accepted within two weeks."])
        self.assertEqual([(x["earlier"], x["now"]) for x in c[1]], [("30", "14")])

    def test_same_limit_in_other_units_is_clean(self):
        c = self.conflicts(["You have 14 days to return it.", "The return window is two weeks."])
        self.assertEqual(c[1], [])


if __name__ == "__main__":
    unittest.main()
