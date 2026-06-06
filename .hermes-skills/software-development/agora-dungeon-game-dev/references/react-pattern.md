# ReAct Pattern — Perceive → Decide → Act Loop

## From "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., arXiv:2210.03629)

## Core Loop
```
1. OBSERVATION ← game state / environment / user input
2. REASONING ← LLM thinks: "I see X, current goal is Y, so I should..."
3. ACTION ← LLM outputs structured action: {action: "move_north", params: {}}
4. EXECUTION ← game engine runs action, returns new observation
5. REPEAT
```

## Implementation in Agora Dungeon

```typescript
interface ReActLoop {
  state: GameState;
  agent: AgentMemory;
  
  async step(): Promise<Action> {
    // 1. Observe
    const observation = this.serializeGameState();
    
    // 2. Reason + Act (single LLM call with structured output)
    const response = await llm.complete({
      messages: [
        {role: "system", content: this.buildSystemPrompt()},
        {role: "user", content: `Observation: ${observation}\n\nThink step by step, then output action.`}
      ],
      response_format: {type: "json_object"}
    });
    
    const {thought, action} = JSON.parse(response);
    
    // 3. Execute
    this.agent.memory.push({observation, thought, action});
    return action;
  }
}
```

## Key Design Rules
- **Single LLM call per step**: reasoning + action in one call (not chain-of-thought + separate action)
- **Structured JSON output**: `{thought: "...", action: "move_north" | "use_workbench" | "talk:target" | "craft:item"}`
- **Game state serialization**: concise, relevant, token-efficient — NOT full game state dump
- **Action space is a small menu** (5-10 actions), not free-form
