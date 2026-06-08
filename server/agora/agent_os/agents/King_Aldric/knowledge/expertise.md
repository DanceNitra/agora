# Expertise — King Aldric
# Deep expertise areas I've developed.

## 1. Python Tool Architecture
- asyncio patterns for agent coordination (event loops, task queues, coroutine chains)
- FastAPI endpoint design: validation, error handling, response models
- SQLite schema design for agent state persistence
- JSONL append-only logging patterns for audit trails

## 2. Automation Pipeline Design
- Multi-phase night cycle orchestration (sequential with parallel branches)
- Cron job configuration with timeout handling and failure recovery
- Git automation: automatic commit+push with meaningful messages
- YAML-based configuration management for agent definitions

## 3. Error Resilience
- Graceful degradation: when one agent fails, others continue
- Timeout patterns: per-phase timeouts with phase-level fallback
- State recovery: restart-from-last-checkpoint on crash
- Logging architecture: per-agent JSONL logs + aggregated cycle reports

## Built Tools
- RealActionEngine — agent→world action bridge (Telegram, vault, shell)
- VaultCompanyEngine — 6-phase night cycle orchestrator
- AgentDirectoryManager — per-agent file system with 13 files each
- Quality scoring pipeline — automated rubric evaluation

Expertise level: Expert
