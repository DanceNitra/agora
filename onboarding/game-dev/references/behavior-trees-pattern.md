# Behavior Trees for NPC AI

## From "Behavior Trees in Robotics and AI" (Colledanchise & Ögren, arXiv:1709.00084)

## Core Nodes

### Control Flow Nodes
```
Sequence (→)   : runs children in order, returns FAILURE if any child fails
Selector (? )  : runs children in order, returns SUCCESS if any child succeeds
Parallel (⇉)   : runs all children simultaneously
Decorator (◉)  : modifies child result (invert, repeat, timeout, etc.)
```

### Execution Nodes
```
Action (▶)     : performs an action, returns SUCCESS/FAILURE/RUNNING
Condition (?)  : checks a condition, returns SUCCESS/FAILURE
```

## NPC Behavior Tree for Dungeon

```
Selector: PRIORITY
├── Sequence: EMERGENCY
│   ├── Condition: Health < 20%
│   └── Action: Flee to safe zone
├── Sequence: WORK (when idle)
│   ├── Condition: Has task assigned
│   ├── Action: Navigate to workbench
│   ├── Action: Perform task
│   └── Action: Report completion
├── Sequence: EXPLORE
│   ├── Condition: No task && energy > 50
│   ├── Action: Pick random room
│   └── Action: Wander to room
└── Action: IDLE (default)
    └── Action: Stand still, observe
```

## LLM Integration (Phase 2+)

```
Selector: PRIORITY
├── Sequence: LLM DECISION (expert override)
│   ├── Condition: LLM connected && has API quota
│   ├── Action: LLMThink (ReAct-style)
│   └── Action: ExecuteLLMAction
├── ... (FSM/Behavior Tree fallback)
└── Action: IDLE
```

The LLM is just **one leaf node** in the behavior tree — same interface, swappable.
