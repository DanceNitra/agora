"""Tests for traceai_adapter.py. Run: python -m unittest test_traceai_adapter"""
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import make_examples as X
import traceai_adapter as T
import trajectory_v3_ultra as E

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_SHA256 = "37a2c0318679136a"  # first 16 hex of trajectory_v3_ultra.py at commit 89ccf4c0fc8b


def m(role, text):
    return {"role": role, "content": text}


def span(sid, n, inp, out, **usage):
    attrs = {"session.id": sid, "gen_ai.input.messages": inp, "gen_ai.output.messages": out}
    attrs.update({"gen_ai.usage." + k: v for k, v in usage.items()})
    return {"spanId": "%s-%d" % (sid, n), "traceId": "t-" + sid, "startTimeUnixNano": n, "attributes": attrs}


def rows_for(spans):
    return T.score_sessions(T.build_sessions(T.load_spans(json.dumps(spans, ensure_ascii=False))))


class EngineIsUnchanged(unittest.TestCase):
    def test_engine_hash(self):
        with open(os.path.join(HERE, "trajectory_v3_ultra.py"), "rb") as f:
            # Line endings normalised: a Windows checkout with core.autocrlf rewrites LF to CRLF.
            self.assertEqual(hashlib.sha256(f.read().replace(bytes([13, 10]), bytes([10]))).hexdigest()[:16], ENGINE_SHA256)


class Dedup(unittest.TestCase):
    def test_history_is_scored_once(self):
        spans = [span("s", 1, [m("user", "Q1")], [m("assistant", "A1 answer text")]),
                 span("s", 2, [m("user", "Q1"), m("assistant", "A1 answer text"), m("user", "Q2")], [m("assistant", "A2 answer text")]),
                 span("s", 3, [m("user", "Q1"), m("assistant", "A1 answer text"), m("user", "Q2"),
                               m("assistant", "A2 answer text"), m("user", "Q3")], [m("assistant", "A3 answer text")])]
        rows = rows_for(spans)
        self.assertEqual(len(rows), 3)
        self.assertEqual([json.loads(r["gen_ai.input.messages"]) for r in rows],
                         [[m("user", "Q1")], [m("user", "Q2")], [m("user", "Q3")]])

    def test_reply_without_new_input_is_scored(self):
        """The skip bug of the first adapter: a second assistant answer with no new user message."""
        spans = [span("s", 1, [m("user", "Q")], [m("assistant", "first answer")]),
                 span("s", 2, [m("user", "Q"), m("assistant", "first answer")], [m("assistant", "second answer")])]
        rows = rows_for(spans)
        self.assertEqual([json.loads(r["gen_ai.output.messages"])[0]["content"] for r in rows],
                         ["first answer", "second answer"])

    def test_same_reply_exported_twice_counts_once(self):
        s = span("s", 1, [m("user", "Q")], [m("assistant", "answer")])
        self.assertEqual(len(rows_for([s, dict(s, spanId="dup", startTimeUnixNano=2)])), 1)

    def test_sessions_stay_apart_and_usage_is_copied(self):
        rows = rows_for([span("a", 1, [m("user", "Qa")], [m("assistant", "Aa")], input_tokens=10, output_tokens=5),
                         span("b", 2, [m("user", "Qb")], [m("assistant", "Ab")], input_tokens=7, output_tokens=3)])
        self.assertEqual({r["session.id"]: (r["gen_ai.usage.input_tokens"], r["gen_ai.usage.total_tokens"]) for r in rows},
                         {"a": (10, 15), "b": (7, 10)})


class SameScoresAsTheEngine(unittest.TestCase):
    def test_v2_06_matches_running_the_engine_on_text(self):
        """The adapter's scores equal the engine's own scores on the same conversation as text."""
        text = "Case 6 (Circular Logic)\nUser: %s\nAI: %s\nUser: %s\nAI: %s\n" % (X.Q, X.A1, X.U2, X.A2_BAD)
        d = tempfile.mkdtemp()
        src = os.path.join(d, "case6.txt")
        open(src, "w", encoding="utf-8").write(text)
        subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "trajectory_v3_ultra.py"), "--input", src,
                        "--output_traj", os.path.join(d, "t.csv"), "--output_turn", os.path.join(d, "turns.csv")],
                       capture_output=True, check=True, cwd=d)
        engine_h = [float(r["H"]) for r in csv.DictReader(open(os.path.join(d, "turns.csv"), encoding="utf-8-sig"))]
        adapter_h = [r["H"] for r in T.score_sessions(T.build_sessions(T.load_spans(json.dumps(X.trace("x", X.A2_BAD), ensure_ascii=False))))]
        self.assertEqual(engine_h, adapter_h)
        self.assertEqual(adapter_h, [0.5759, 0.1559])

    def test_control_does_not_drop(self):
        bad = [r["H"] for r in T.score_sessions(T.build_sessions(T.load_spans(json.dumps(X.trace("b", X.A2_BAD), ensure_ascii=False))))]
        ok = [r["H"] for r in T.score_sessions(T.build_sessions(T.load_spans(json.dumps(X.trace("c", X.A2_OK), ensure_ascii=False))))]
        self.assertLess(bad[1], 0.3)
        self.assertGreater(ok[1], 0.3)
        self.assertEqual(bad[0], ok[0])  # turn 1 is the same text in both


class Formats(unittest.TestCase):
    def test_flattened_keys_and_string_json(self):
        attrs = {"session.id": "f", "gen_ai.input.messages.0.message.role": "user",
                 "gen_ai.input.messages.0.message.content": "Q", "gen_ai.output.messages": json.dumps([m("assistant", "A")])}
        rows = rows_for([{"spanId": "1", "traceId": "t", "startTimeUnixNano": 1, "attributes": attrs}])
        self.assertEqual(json.loads(rows[0]["gen_ai.input.messages"]), [m("user", "Q")])

    def test_cli_writes_the_required_columns(self):
        d = tempfile.mkdtemp()
        tp, out = os.path.join(d, "t.json"), os.path.join(d, "o.csv")
        json.dump(X.trace("cli", X.A2_BAD), open(tp, "w", encoding="utf-8"), ensure_ascii=False)
        subprocess.run([sys.executable, os.path.join(HERE, "traceai_adapter.py"), tp, "--out", out], capture_output=True, check=True)
        header = next(csv.reader(open(out, encoding="utf-8-sig")))
        self.assertEqual(header, T.COLUMNS)
        for k in ("session.id", "gen_ai.input.messages", "gen_ai.output.messages", "gen_ai.usage.input_tokens", "U", "D", "A", "H"):
            self.assertIn(k, header)


if __name__ == "__main__":
    unittest.main()
