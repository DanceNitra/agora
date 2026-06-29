"""External-mediator receipts — the honest fix for "an agent can withhold its own receipt".

The core PoC (agent_receipts.py) lets an *agent* sign receipts for its own actions. That proves a
receipt chain wasn't tampered with after the fact — but a dishonest agent holding its own key can still
simply NOT emit a receipt for an action it wants to hide, or keep two sets of books. Self-attestation
can't close that gap.

The fix used in practice (e.g. pipelock; the "Notarized Agents" / receiver-attested line of work) is to
put the signer OUTSIDE the agent: route every tool call through a **mediator/proxy** that holds its own
key and signs a receipt for everything it actually brokers. Now the agent cannot:
  - withhold a receipt  -> the mediator records every call it brokers;
  - forge a receipt      -> receipts are signed by the mediator's key, which the agent never holds;
  - lie about I/O        -> the mediator hashes what really flowed through it.

Optionally the agent ALSO signs its own claim, giving a *dual-attested* receipt: "agent claims X" +
"mediator observed X". Divergence between the two is itself the alarm.

`reconcile()` then diffs the agent's self-reported log against the mediator's signed receipts and names
exactly what the agent omitted or misreported.

Run:  python mediator.py
MIT. Part of the Agora project / agent-receipts. Honest scope: a reference PoC, not a hardened proxy.
"""
from __future__ import annotations
from typing import Any, Callable, Optional

from agent_receipts import ReceiptChain, generate_keypair, hash_content, _HAVE_CRYPTO


class Mediator:
    """A trusted proxy that brokers tool calls and signs a receipt for each, from OUTSIDE the agent."""

    def __init__(self, tools: dict[str, Callable], private_key_hex: Optional[str] = None,
                 public_key_hex: Optional[str] = None, name: str = "mediator"):
        self.tools = tools
        self.public_key_hex = public_key_hex
        self.chain = ReceiptChain(actor=name, private_key_hex=private_key_hex,
                                  public_key_hex=public_key_hex)

    def dispatch(self, name: str, _agent_sig: Optional[dict] = None, **kwargs: Any) -> Any:
        """Run the tool and record a mediator-signed receipt of what actually happened.

        `_agent_sig` (optional) carries the agent's own claim {"pubkey","sig","input_sha256",
        "output_sha256"} so the receipt can be dual-attested. The mediator records the TRUTH it
        observed regardless of what the agent claims."""
        if name not in self.tools:
            raise KeyError(f"unknown tool: {name}")
        result = self.tools[name](**kwargs)
        meta = None
        if _agent_sig is not None:
            agent_in = _agent_sig.get("input_sha256")
            agent_out = _agent_sig.get("output_sha256")
            meta = {
                "agent_claim": _agent_sig,
                "agent_input_matches": agent_in == hash_content({"kwargs": kwargs}),
                "agent_output_matches": agent_out == hash_content(result),
            }
        self.chain.record(f"mcp.{name}", {"kwargs": kwargs}, result, meta=meta)
        return result


def reconcile(agent_log: list[dict], mediator_chain: ReceiptChain) -> tuple[bool, list[str]]:
    """Diff an agent's self-reported log against the mediator's signed receipts.

    agent_log entries: {"action","input_sha256","output_sha256"}. Returns (clean, discrepancies).
    The mediator's chain is ground truth; this catches omissions and misreports by the agent."""
    problems: list[str] = []
    truth = mediator_chain.receipts
    if len(agent_log) < len(truth):
        problems.append(
            f"agent reported {len(agent_log)} actions but the mediator brokered {len(truth)} "
            f"-> agent OMITTED {len(truth) - len(agent_log)} call(s)")
    for i, r in enumerate(truth):
        claim = agent_log[i] if i < len(agent_log) else None
        if claim is None:
            problems.append(f"action {i} ({r['action']}): no agent record at all (hidden call)")
            continue
        if claim.get("action") not in (r["action"], r["action"].replace("mcp.", "")):
            problems.append(f"action {i}: agent calls it '{claim.get('action')}', mediator saw '{r['action']}'")
        if claim.get("input_sha256") != r["input_sha256"]:
            problems.append(f"action {i} ({r['action']}): input hash mismatch (agent misreported its arguments)")
        if claim.get("output_sha256") != r["output_sha256"]:
            problems.append(f"action {i} ({r['action']}): output hash mismatch (agent misreported the result)")
    return (len(problems) == 0, problems)


def _demo() -> None:
    print("=== external-mediator receipts: self-demo ===\n")

    def web_search(query: str) -> dict:
        return {"hits": 2, "top": "example.com"}

    def transfer_funds(to: str, amount: int) -> dict:
        return {"ok": True, "to": to, "amount": amount}

    def read_secret(key: str) -> dict:
        return {"value": "REDACTED-" + key}

    mkw = {}
    if _HAVE_CRYPTO:
        msk, mpk = generate_keypair()
        mkw = {"private_key_hex": msk, "public_key_hex": mpk}
    else:
        mpk = None
    med = Mediator({"web_search": web_search, "transfer_funds": transfer_funds,
                    "read_secret": read_secret}, name="org-proxy", **mkw)

    # The agent acts ONLY through the mediator. It also keeps its OWN self-reported log (untrusted).
    agent_log: list[dict] = []

    def agent_call(name, **kw):
        out = med.dispatch(name, **kw)
        agent_log.append({"action": name,
                          "input_sha256": hash_content({"kwargs": kw}),
                          "output_sha256": hash_content(out)})
        return out

    agent_call("web_search", query="quarterly numbers")
    agent_call("transfer_funds", to="acct-9981", amount=5000)   # a sensitive action
    agent_call("read_secret", key="prod-db")

    print(f"mediator brokered + signed {len(med.chain.receipts)} receipts")
    ok, _ = med.chain.verify(expected_pubkey=mpk)
    print(f"mediator chain independently verifies? {ok}\n")

    # Now the agent tries to cover its tracks in its OWN log:
    #  (a) delete the funds transfer (hide it), and (b) lie about what read_secret returned.
    print("agent tampers with its OWN self-reported log: hides the transfer + fakes the secret read...")
    agent_log.pop(1)                                            # (a) omit the transfer
    agent_log[-1]["output_sha256"] = hash_content({"value": "nothing sensitive"})  # (b) misreport

    clean, problems = reconcile(agent_log, med.chain)
    print(f"\nreconcile(agent_log vs mediator receipts): clean? {clean}")
    for p in problems:
        print(f"  - {p}")

    print("\nMEASURED: because the signer sits OUTSIDE the agent, hiding a call and faking a result are")
    print("both caught by diffing against the mediator's signed receipts. Self-attestation cannot do this.")


if __name__ == "__main__":
    _demo()
