"""Does CrewAI let the saver replace a tool result? Measured by running CrewAI's own code.

The survey said CrewAI's after-tool hook can modify the result, on the strength of reading
`modified_result = run_after_tool_call_hooks(...)` in crewai/agents/crew_agent_executor.py. That
is a reading, not a measurement, and the owner was right to call it out: a field can be read and
then ignored, which is exactly what the OpenAI Agents SDK does with on_tool_end.

So this calls CrewAI's real tool-execution method, `CrewAgentExecutor._execute_single_native_tool_call`,
with a tool that returns 8 KB, and checks what the executor hands back.

Controls, both directions:
  - with no hook registered, the raw output must come back whole. Otherwise the digest below
    proves nothing about the hook.
  - a hook that returns None must leave the result untouched: that is how CrewAI distinguishes
    an observer from a replacement.
  - the digest must be shorter than the output AND name the capture file, or it is not the
    saver's replacement.

No LLM call and no network: the executor is driven directly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

RESULT = Path(__file__).with_suffix(".result.json")
BIG = "\n".join("line %d: hydraulic pressure curve sample row" % i for i in range(300))
INTENT = "read the pressure curve rows"


def run_executor(hook):
    """CrewAI's own tool-execution path, with `hook` registered as its after-tool hook."""
    from crewai.agents.crew_agent_executor import CrewAgentExecutor
    from crewai.hooks import clear_after_tool_call_hooks, register_after_tool_call_hook

    clear_after_tool_call_hooks()
    if hook is not None:
        register_after_tool_call_hook(hook)

    # model_construct, not __new__: CrewAgentExecutor is a pydantic model, and bypassing its
    # constructor leaves __pydantic_fields_set__ missing, so the first attribute write raises.
    handler = MagicMock(name="tools_handler")
    handler.cache = None
    # CrewAI emits pydantic-validated events about the call, so role and key must be real
    # strings. A MagicMock fails validation inside the event, not in the hook under test.
    agent = MagicMock(name="agent")
    agent.role = "probe-agent"
    agent.key = "probe-key"
    # A real CrewAI tool, because the method resolves the call against self.tools and returns
    # "Tool not found" for anything else. That string is 14 bytes, which is what the first run
    # of this probe measured for all three arms.
    from crewai.tools import tool as crewai_tool

    @crewai_tool("read_rows")
    def read_rows(path: str) -> str:
        """Read the pressure curve rows."""
        return BIG

    structured = read_rows.to_structured_tool() if hasattr(read_rows, "to_structured_tool") else read_rows
    executor = CrewAgentExecutor.model_construct(
        agent=agent, task=None, crew=None, tools_handler=handler,
        tools=[structured], original_tools=[read_rows], tools_names="read_rows",
        function_calling_llm=None, step_callback=None)

    out = executor._execute_single_native_tool_call(
        call_id="call-1",
        func_name="read_rows",
        func_args={"path": "rows.txt"},
        available_functions={"read_rows": lambda **_: BIG},
        original_tool=read_rows,
    )
    clear_after_tool_call_hooks()
    return out


def digest_hook(context):
    """The saver, as a CrewAI after-tool hook."""
    from inspeximus.context_saver import SEPARATOR, new_capture_path, save

    output = context.tool_result
    if not isinstance(output, str) or len(output) < 2000:
        return None
    result = save(output, INTENT, without_reranker="hybrid", ranking="lexical")
    if result["mode"] == "passthrough":
        return None
    where = new_capture_path()
    Path(where).write_text(output, encoding="utf-8")
    return SEPARATOR.join(["[inspeximus] digest of the full output", result["text"],
                           "full output: %s" % where])


def text_of(out):
    """The model-visible text, whatever shape the executor returns it in."""
    if isinstance(out, str):
        return out
    if isinstance(out, dict):
        for key in ("content", "result", "output", "text"):
            value = out.get(key)
            if isinstance(value, str):
                return value
    return str(out)


def main() -> int:
    import crewai

    control = text_of(run_executor(None))
    observer = text_of(run_executor(lambda ctx: None))
    digested = text_of(run_executor(digest_hook))

    findings = {
        "measured": "2026-10-29",
        "crewai": crewai.__version__,
        "output_bytes": len(BIG),
        "no_hook_bytes": len(control),
        "observer_hook_bytes": len(observer),
        "digest_hook_bytes": len(digested),
        "controls": {
            "no_hook_keeps_the_whole_output": BIG in control,
            "an_observer_hook_changes_nothing": observer == control,
        },
        "verdict": None,
    }
    ok = (findings["controls"]["no_hook_keeps_the_whole_output"]
          and findings["controls"]["an_observer_hook_changes_nothing"]
          and len(digested) < len(control)
          and "full output: " in digested)
    findings["verdict"] = "REPLACED" if ok else "NOT REPLACED"
    RESULT.write_text(json.dumps(findings, indent=1), encoding="utf-8")

    print("crewai %s: output %d bytes" % (crewai.__version__, len(BIG)))
    print("  no hook        -> %6d bytes, holds the whole output: %s"
          % (len(control), findings["controls"]["no_hook_keeps_the_whole_output"]))
    print("  observer hook  -> %6d bytes, unchanged: %s"
          % (len(observer), findings["controls"]["an_observer_hook_changes_nothing"]))
    print("  digest hook    -> %6d bytes, names its capture file: %s"
          % (len(digested), "full output: " in digested))
    print("verdict: %s" % findings["verdict"])
    print("result: %s" % RESULT)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
