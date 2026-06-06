# Generative Agents — Full Architecture Implementation Details

## From UIST '23 paper by Park et al. (arXiv:2304.03442)
## The definitive reference for your Agora Dungeon project

## 1. Memory Stream

### Structure
```typescript
interface MemoryObject {
  id: string;
  description: string;        // Natural language
  created_at: number;          // Game timestamp
  last_accessed_at: number;    // For recency decay
  importance: number;          // 1-10, LLM-scored at creation
  embedding: number[];         // For relevance (cosine similarity)
  type: 'observation' | 'reflection' | 'plan';
  citations?: string[];        // For reflections: pointers to source memories
}
```

### Retrieval Scoring
```
score = recency + importance + relevance
(All alpha weights = 1.0 in paper)

recency = decay ^ hours_since_last_access
  decay = 0.995

importance = LLM scores at creation time
  Prompt: "On scale 1-10, where 1 is purely mundane (brushing teeth, making bed)
           and 10 is extremely poignant (break up, college acceptance),
           rate the poignancy of: [memory]"

relevance = cosine_similarity(embedding(memory), embedding(query))
```

### Importance Examples
| Memory | Score |
|--------|:-----:|
| "cleaning up the room" | 2 |
| "buying groceries" | 2 |
| "asking your crush out on a date" | 8 |
| "breakup with significant other" | 10 |

## 2. Reflection System

### Trigger Condition
```
When SUM(importance of latest events) > 150
→ Generate reflections (~2-3 times per game day)
```

### Reflection Generation (2 steps)
```
Step 1 — Question Generation:
  Input: 100 most recent memory stream records
  Prompt: "Given only the information above,
           what are 3 most salient high-level questions
           we can answer about the subjects in the statements?"
  Output: e.g., "What topic is Klaus Mueller passionate about?"

Step 2 — Insight Extraction:
  For each question:
    - Use question as retrieval query
    - Gather relevant memories + other reflections
    - Prompt: "Statements about [agent]
               1. [memory 1]
               2. [memory 2]
               ...
               What 5 high-level insights can you infer?
               (format: insight (because of 1, 5, 3))"
  Output: "Klaus Mueller is dedicated to his research
           on gentrification (because of 1, 2, 8, 15)"
```

### Reflection Trees
Reflections can reflect on other reflections:
- Leaf nodes = base observations
- Non-leaf nodes = increasingly abstract thoughts
- Stored in memory stream alongside observations
- Retrieved just like any other memory

## 3. Planning (Recursive Decomposition)

### Level 1 — Daily Plan (5-8 chunks)
```
Prompt: [Agent summary description + yesterday's summary]
        "Today is [day]. Here is [agent]'s plan today in broad strokes: 1)"
Output: "1) wake up and complete morning routine at 8:00 am,
         2) go to Oak Hill College for classes at 10:00 am,
         3) work on music composition 1:00 pm to 5:00 pm,
         4) have dinner at 5:30 pm,
         5) finish assignments and bed by 11:00 pm"
```

### Level 2 — Hour-level actions
```
From "work on composition 1-5pm":
  → 1:00 pm: brainstorm ideas for music composition
  → 2:00 pm: develop main theme
  → 3:00 pm: review and refine
  → 4:00 pm: take break, recharge
```

### Level 3 — 5-15 minute granularity
```
From "4:00 pm: take break":
  → 4:00 pm: grab light snack
  → 4:05 pm: short walk around workspace
  → 4:50 pm: clean up workspace
```

### Plan Entry in Memory
```
{location, start_time, duration, description}
Example: for 180 minutes from 9am, Feb 12,
         at Oak Hill College Dorm: room: desk,
         "read and take notes for research paper"
```

## 4. Reacting & Action Loop

### Per Time Step
```
1. Perceive world → store observations in memory stream
2. Retrieve relevant context (memory + plans + reflections)
3. Decide: continue current plan OR react?
   - If plan fits observation → continue (e.g., standing at easel painting)
   - If unexpected event → react (e.g., seeing son walking during work hours)
4. If react: regenerate plan from current time
5. If interaction: generate dialogue
```

### Reaction Prompt
```
[Agent's Summary Description]
It is [date], [time].
[Agent]'s status: [current status]
Observation: [what agent perceived]
Summary of relevant context from [agent]'s memory:
  [retrieved memories about the observed entity/event]
Should [agent] react to the observation, and if so,
what would be an appropriate reaction?
```

## 5. Dialogue Generation

### When Agent A initiates conversation with Agent B:
```
Prompt for A:
  [A's summary description + time + status + observation]
  [A's memory summary about B]
  "A is [action]. What would A say to B?"
```

### When B responds:
```
Prompt for B:
  [B's summary description + time + status]
  [B's memory summary about A + about the topic]
  [Dialogue history so far]
  "How would B respond to A?"
```

Continues until one agent decides to end the conversation.

## 6. Environment Tree

### Structure
```
World (Smallville)
├── The Lin family's house
│   ├── kitchen
│   │   ├── stove
│   │   ├── refrigerator
│   │   └── sink
│   ├── bedroom
│   │   ├── bed
│   │   ├── desk
│   │   └── closet
│   └── garden
│       └── house garden
├── Hobbs Cafe
│   ├── counter
│   │   └── coffee machine
│   └── tables
├── Johnson Park
└── Oak Hill College
```

### Agent's Subgraph
- Each agent has INDIVIDUAL tree (not omniscient)
- Initialized with known areas: home, workplace, common places
- Updated as agent explores (forgets when leaves, re-learns on return)
- Can become outdated between visits

### Location Selection
```
Recursive: root → child → child → leaf
At each level: LLM chooses most appropriate area
Prompt includes:
  - Agent's current location
  - Known areas list
  - "Prefer to stay in current area if activity can be done there"
Output: leaf node (e.g., "The Lin family's house: garden: house garden")
```

### Navigation
- LLM selects target location via tree
- Traditional pathfinding (A* / Dijkstra) for actual movement
- Agent moves smoothly in Phaser

## 7. Sandbox Server (JSON-based)

### State Structure
```json
{
  "agents": [
    {
      "id": "isabella_rodriguez",
      "location": "Hobbs Cafe: counter",
      "action": "making espresso for a customer",
      "interacting_with": "coffee_machine"
    }
  ],
  "objects": [
    {
      "id": "coffee_machine",
      "location": "Hobbs Cafe: counter",
      "status": "brewing coffee"
    }
  ]
}
```

### Tick Loop
```
1. Parse JSON for agent state changes
2. Move agents to new positions (A* pathfinding)
3. Update object states based on agent actions
4. Send visible agents/objects to each agent's memory
5. Wait for LLM to respond with next action
6. Update JSON → loop
```

## 8. Key Implementation Numbers
| Parameter | Value |
|:----------|:-----:|
| Memory decay factor | 0.995 per game hour |
| Reflection threshold | sum(importance) > 150 |
| Reflections per day | ~2-3 |
| LLM used | GPT-3.5-turbo (ChatGPT) |
| Game framework | Phaser 3 |
| Server framework | Django |
| Agent summary | Paragraph generated dynamically (Appendix A) |
| Embedding model | text-embedding-ada-002 |

## 9. Critical Design Insights for Your Project

1. **Everything is natural language** — environment, actions, memories, reflections
2. **LLM is CONSTANTLY called** — at every time step for every agent (expensive!)
3. **Memory retrieval is the bottleneck** — get recency/importance/relevance right
4. **Reflection prevents memory loss** — compresses raw observations into insights
5. **Plans in memory stream** — allows reconsideration, not rigid scripts
6. **Environment tree + pathfinding** — LLM decides WHERE, game engine decides HOW
7. **JSON server pattern** — simple, works well with Phaser
8. **Agent summary evolves** — initial description, then shaped by experiences
