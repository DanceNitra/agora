"""Make every MCP / agent tool call emit a verifiable receipt — with one wrapper.

This shows the practical point of agent-receipts: you don't change your tools, you wrap the dispatch.
Each call commits to (tool name, arguments-hash, result-hash) in a signed, hash-chained receipt, so
afterwards anyone can verify *what the agent actually called and got back* — independently of the
agent's own logs.

Run:  python mcp_wrapper.py
"""
from __future__ import annotations
from typing import Any, Callable
from agent_receipts import ReceiptChain, generate_keypair, _HAVE_CRYPTO


def receipted_tool(chain: ReceiptChain, fn: Callable, action: str | None = None) -> Callable:
    """Wrap a single tool callable so each invocation appends a receipt to `chain`."""
    name = action or getattr(fn, "__name__", "tool")

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = fn(*args, **kwargs)
        chain.record(name, {"args": args, "kwargs": kwargs}, result)
        return result

    return wrapped


class ReceiptedDispatcher:
    """Drop-in around an MCP-style tool registry: dispatch(name, **kwargs) -> result, receipt recorded."""

    def __init__(self, chain: ReceiptChain, tools: dict[str, Callable]):
        self.chain = chain
        self.tools = tools

    def dispatch(self, name: str, **kwargs: Any) -> Any:
        if name not in self.tools:
            raise KeyError(f"unknown tool: {name}")
        result = self.tools[name](**kwargs)
        self.chain.record(f"mcp.{name}", {"kwargs": kwargs}, result)
        return result


def _demo() -> None:
    # two example "MCP tools"
    def web_search(query: str) -> dict:
        return {"hits": 3, "top": "example.com/" + query.replace(" ", "-")}

    def calculator(expr: str) -> dict:
        return {"value": eval(expr, {"__builtins__": {}})}  # demo only; never eval untrusted input

    kw = {}
    if _HAVE_CRYPTO:
        sk, pk = generate_keypair()
        kw = {"private_key_hex": sk, "public_key_hex": pk}
    else:
        pk = None
    chain = ReceiptChain(actor="agent-with-receipts", **kw)

    bus = ReceiptedDispatcher(chain, {"web_search": web_search, "calculator": calculator})
    bus.dispatch("web_search", query="verifiable agent receipts")
    bus.dispatch("calculator", expr="6*7")

    print("=== mcp_wrapper: self-demo ===")
    print(chain.to_json())
    ok, problems = chain.verify(expected_pubkey=pk)
    print(f"\nindependently verifiable? {ok}  {problems if problems else ''}")
    print("Anyone holding only the public key can confirm exactly which tools ran, with which")
    print("argument/result hashes, in which order — without trusting the agent's own logs.")


if __name__ == "__main__":
    _demo()
