# Generative Agents Architecture

## From "Generative Agents: Interactive Simulacra of Human Behavior" (Park et al., arXiv:2304.03442)

## Three Core Systems

### 1. Memory Stream
- All agent experiences stored as chronological events
- Each event has: `{timestamp, content, importance, embeddings}`
- **Importance scoring**: LLM self-rates events (1-9 scale)
- **Recency + Relevance + Importance** → retrieval weight formula

```typescript
interface MemoryEvent {
  id: string;
  timestamp: number;
  content: string;
  importance: number;   // 1-9, LLM-scored
  embedding: number[];  // for semantic retrieval
  type: 'observation' | 'reflection' | 'conversation';
}
```

### 2. Reflection (Higher-Level Reasoning)
- Every N events or when important event occurs → LLM reflects
- Asks: "What 3 most salient high-level insights can you infer?"
- Reflections are stored back in memory stream
- Enables agents to learn from experience

### 3. Planning & Reacting
- **Daily plan**: LLM generates rough schedule at start of day
- **Action**: LLM decides moment-by-moment actions
- **Reaction**: LLM responds to unexpected events

## Architecture for Agora Dungeon

```typescript
class AgentBrain {
  memory: MemoryStream;
  reflection: ReflectionSystem;
  
  async decideAction(observation: GameState): Promise<Action> {
    // 1. Retrieve relevant memories
    const memories = this.memory.query(observation);
    
    // 2. Fast planning (ReAct-style)
    const plan = await this.llm.think(observation, memories);
    
    // 3. After N actions → reflect
    if (this.memory.eventsSinceLastReflection > 20) {
      const insights = await this.reflection.generate(this.memory);
      this.memory.add(insights);
    }
    
    return plan;
  }
}
```

## Key Patterns to Steal
1. **Importance-weighted memory**: not all memories equal
2. **Reflection as compression**: summarize experiences into insights
3. **Plan → Act → React**: tiered decision making
4. **Environment broadcasts**: world events appear in agent memory
5. **Conversation as memory**: social interactions stored like observations
