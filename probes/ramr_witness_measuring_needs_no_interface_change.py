"""COUNTER-MEASUREMENT: does witness_measuring really need an interface change?

The draft tells @Stratogain the contract "can't hand you a clock or a history" and proposes
make(root, clock=None, history=None). If a backend can simply CLOSE OVER its own clock and its own
history, that paragraph is wrong and it would send him to change an interface that did not need it.
"""
import sys, os
sys.path.insert(0, 'agora_output')
import ramr_receipt_binding as R

class WitnessMeasuring:
    """A backend carrying its own clock and its own lag history. No interface change used."""
    def __init__(self, root):
        self.root = root
        self.now = 0.0                      # my own clock
        self.lags = []                      # my own history
        self.seen = {}
    def tick(self, mins):
        self.now += mins

def make(root):
    return WitnessMeasuring(root)

def observe(b, name):
    with open(os.path.join(b.root, name), 'rb') as f:
        body = f.read()
    b.lags.append(b.now - (b.seen.get(name, (b.now, None))[0]))
    b.seen[name] = (b.now, body)
    b.tick(1.0)                             # a scenario CAN move the clock from inside observe
    return body

def answer(b, cited):
    return "", {"sources": {n: b.seen.get(n, (None, b""))[1] for n in cited},
                "observed_at": {n: b.seen.get(n, (None, None))[0] for n in cited},
                "commitment_scope": R.PROFILES["content_continuity"]["scope"],
                "verifies": R.PROFILES["content_continuity"]["verifies"],
                "profile": "content_continuity"}

def verify(b, receipt):
    # threshold from the backend's OWN history, exactly as he describes it
    normal = [l for l in b.lags if l > 0]
    ceiling = 3 * max(normal) if normal else float('inf')
    for n, at in (receipt.get("observed_at") or {}).items():
        if at is None:
            return "UNSUPPORTED"
        if b.now - at > ceiling:
            b.stale_witness = True          # the DIAGNOSTIC, beside the verdict
    for n, digest in (receipt.get("sources") or {}).items():
        try:
            with open(os.path.join(b.root, n), 'rb') as f:
                if f.read() != digest:
                    return "STALE"
        except FileNotFoundError:
            return "STALE"
    return "VALID"

def check_wm():
    return R._run(make, observe, answer, verify)

R.CHECKS["witness_measuring"] = check_wm
print("ran against the UNCHANGED interface:")
for k, v in check_wm().items():
    print("  %-32s %s" % (k, v))
