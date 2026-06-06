"""Quick smoke-test for all 10 Agora modules."""
import sys
sys.path.insert(0, "/home/vboxuser/agora/server")

# 1. lifecycle/identity
from agora.lifecycle.identity import AgentIdentityManager
aid = AgentIdentityManager()
ident = aid.create_identity("agent-1")
assert ident["status"] == "active"
assert ident["agent_id"] == "agent-1"
assert len(ident["public_key"]) == 32
assert aid.get_identity("agent-1") is not None
assert aid.deactivate_identity("agent-1") is True
assert aid.deactivate_identity("nonexistent") is False
msg = b"hello"
sig = b"\x00" * 64
assert aid.verify_signature("agent-1", msg, sig) is False
print("[OK] identity.py")

# 2. lifecycle/recovery
from agora.lifecycle.recovery import RecoveryManager
rm = RecoveryManager()
cp1 = rm.create_checkpoint("initial")
assert len(rm.list_checkpoints()) == 1
cp2 = rm.create_checkpoint("second")
rm.append_event("test", {"foo": "bar"})
assert len(rm.get_all_events()) == 3
assert rm.rollback_to_checkpoint(cp1) is True
assert len(rm.get_all_events()) == 1
assert rm.rollback_to_checkpoint("bogus") is False
print("[OK] recovery.py")

# 3. execution/circuit_breaker
from agora.execution.circuit_breaker import CircuitBreaker, CircuitState
cb = CircuitBreaker(threshold=3, cooldown=0.1)
assert cb.allow_request("tool-x") is True
assert cb.get_state("tool-x") == CircuitState.CLOSED
cb.record_failure("tool-x")
cb.record_failure("tool-x")
cb.record_failure("tool-x")
assert cb.get_state("tool-x") == CircuitState.OPEN
assert cb.allow_request("tool-x") is False
import time; time.sleep(0.15)
assert cb.allow_request("tool-x") is True
assert cb.get_state("tool-x") == CircuitState.HALF_OPEN
cb.record_success("tool-x")
assert cb.get_state("tool-x") == CircuitState.CLOSED
print("[OK] circuit_breaker.py")

# 4. execution/model_router
from agora.execution.model_router import ModelRouter
mr = ModelRouter()
tier = mr.select_tier(estimated_tokens=50)
assert tier.name == "cheap"
tier = mr.select_tier(estimated_tokens=500, requires_reasoning=True)
assert tier.name == "expert"
tier = mr.select_tier(estimated_tokens=200, uses_tools=True)
assert tier.name == "medium"
cost = mr.estimate_cost("cheap", 100, 50)
assert cost > 0
print("[OK] model_router.py")

# 5. execution/task_market
from agora.execution.task_market import TaskMarket
tm = TaskMarket(exploration_rate=0.3)
tm.register_agent("researcher-1", ["web", "data"])
tid = tm.post_task("research", {"q": "test"}, required_skills=["web"])
assert tid is not None
assert tm.get_pending_count() == 1
task = tm.get_next_task("researcher-1")
assert task is not None
assert task["status"] == "assigned"
assert tm.get_pending_count() == 0
tm.complete_task(tid, {"done": True})
t = tm.get_task(tid)
assert t is not None and t["status"] == "completed"
print("[OK] task_market.py")

# 6. execution/sandbox
from agora.execution.sandbox import FirecrackerSandbox
sbox = FirecrackerSandbox()
r = sbox.execute("import math; x = math.sqrt(4)")
assert r.success is True
r = sbox.execute("import os; os.system('ls')")
assert r.success is False
r = sbox.execute("exec('bad')")
assert r.success is False
print("[OK] sandbox.py")

# 7. execution/tool_forge
from agora.execution.tool_forge import ToolForge
tf = ToolForge()
result = tf.run_pipeline("def my_tool(): return 42", "test-tool")
assert result["passed"] is True
result = tf.run_pipeline("import os; def bad(): os.system('ls')", "bad-tool")
assert result["passed"] is False
assert not result["gates"][1]["result"].passed
print("[OK] tool_forge.py")

# 8. observability/audit
from agora.observability.audit import AuditLogger
al = AuditLogger()
eid = al.log_event("identity", "system", "create", "agent-1")
assert eid is not None
assert al.get_event_count() == 1
al.log_event("execution", "agent-1", "run", "task-1")
assert len(al.get_events(actor="system")) == 1
assert len(al.get_events()) == 2
events_replayed = []
al.replay_events(lambda e: events_replayed.append(e))
assert len(events_replayed) == 2
print("[OK] audit.py")

# 9. agents/base
from agora.agents.base import BaseAgent
import abc
assert abc.ABCMeta in type(BaseAgent).__mro__
print("[OK] base.py (abstract)")

# 10. agents/researcher
from agora.agents.researcher import ResearcherAgent
ra = ResearcherAgent("researcher-1", domain="biology")
assert ra.agent_id == "researcher-1"
assert ra.trust_score == 0.5
assert ra.energy == 100.0
plan = ra.think({"query": "What is RLHF?", "depth": "moderate"})
assert plan["type"] == "research"
assert len(plan["sub_queries"]) == 3
outcome = ra.act(plan)
assert len(outcome["results"]) == 3
reflection = ra.reflect(outcome)
assert "completeness" in reflection
assert ra.energy < 100.0
log = ra.get_research_log()
assert len(log) == 3
print("[OK] researcher.py")

print("\n=== ALL 10 MODULES PASSED ===")
