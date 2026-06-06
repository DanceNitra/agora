# Memory Stream Implementation (from Generative Agents)

## Core Data Structure

```typescript
interface Memory {
  id: string;
  description: string;              // Natural language event description
  creation_timestamp: string;       // ISO datetime of recording
  last_access_timestamp: string;    // ISO datetime of last retrieval
  importance_score: number;         // 1-10, LLM-assessed poignancy
  type: 'observation' | 'reflection' | 'plan';
  embedding?: number[];             // Text embedding vector
}
```

## Importance Scoring (LLM Prompt)

```
"On the scale of 1 to 10, where 1 is purely mundane (e.g., brushing teeth, making bed)
and 10 is extremely poignant (e.g., a break up, college acceptance), rate the likely
poignancy of the following piece of memory.
Memory: {description}
Rating: <fill in>"
```

Examples:
- "cleaning up the room" → 2
- "asking your crush out on a date" → 8

## Retrieval Score Formula

```
score(m, q) = α_recency  * recency(m, q)
             + α_importance * importance(m, q)
             + α_relevance  * relevance(m, q)
```

Where **all three components are min-max normalized to [0,1]** before combining.

### Parameters (α weights)
All set to **1.0** in the paper's implementation.

### Recency (Exponential Decay)

```
recency(m, q) = exp(-0.995 * Δt)
```

- **Decay factor λ = 0.995**
- **Δt** = number of sandbox game hours since memory was **last retrieved** (not created)
- Recently accessed memories get higher recency scores

### Relevance (Cosine Similarity)

```
relevance(m, q) = cosine_similarity(embedding(m), embedding(q))
```

- Uses text embedding vectors
- Measures how semantically related a memory is to the current query

### Importance Score (raw value)
Simply the **1-10 importance_score** from the memory object, min-max normalized across all memories.

## Retrieval Process

1. Agent needs to act/react → generates a query
2. For EVERY memory in the stream, calculate score(m, q)
3. Normalize recency, relevance, importance separately via min-max scaling to [0,1]
4. Combine with α weights (all 1.0)
5. Return top-K memories sorted by score

---

## Planning System

### Top-Down Recursive Decomposition

Planning operates **top-down**, starting broad and recursively decomposing:

```
Daily Plan (broad agenda)
  └─ Hourly chunks (e.g., "1:00 pm: start brainstorming...")
       └─ Micro-actions (5-15 min, e.g., "4:00 pm: grab a light snack")
```

### Plan Data Structure

A plan entry must include:
- **location** — where the action takes place
- **starting_time** — when it begins
- **duration** — how long it lasts
- **description** — natural language description of the action

In the memory stream: "for 180 minutes from 9am, February 12th, 2023, at Oak Hill College Dorm: Klaus Mueller's room: desk, read and take notes for research paper"

### Planning Prompt

Fed into LLM: (1) agent's summary description + (2) summary of previous day.
```
[Agent's Summary Description]
[Agent]'s schedule today:
1) Wake up and complete the morning routine at 6:00 am,
2) ...
```

### Reaction System — Continuous Action Loop

```
loop:
  1. Perceive environment → record observation into memory stream
  2. LLM evaluates: continue plan OR react?
  3a. If continue → execute next planned action
  3b. If react → retrieve memories, summarize context,
      determine response, REGENERATE plan from reaction time onward
```

### React Prompt

```
[Agent's Summary Description]
It is {date, time}. [Agent]'s status: {Current Action}
Observation: {What the agent just saw}
Summary of relevant context from memory: {Retrieved context}
Should [Agent] react to the observation, and if so, what would be an appropriate reaction?
```

### Plan Storage

Plans are **first-class objects in the memory stream** (same DB as observations + reflections). Plans are naturally retrieved by memory queries. When plan changes: **new plan replaces from reaction time onward**.

---

## Reflection Tree

### Trigger Condition

A reflection is triggered **periodically** when the **sum of importance scores of the latest events** exceeds **150**.

- In practice: agents reflect **~2-3 times per day**
- Checks the sum of recently perceived events, not the entire memory stream

### Two-Step Reflection Process

**Step 1 — Identify Questions:**
Take the **100 most recent memory records** and prompt the LLM to generate **3 salient high-level questions**.

**Step 2 — Generate Insights:**
For each question, retrieve relevant memories from the entire stream, then prompt the LLM to synthesize **5 high-level insights** with **explicit citations** (memory indices like "because of 1, 5, 3").

### Reflection Data Structure

```typescript
interface Reflection extends Memory {
  type: 'reflection';
  cited_memory_pointers: string[];  // IDs of cited memory objects (edges to parent nodes)
}
```

Example:
```json
{
  "description": "Klaus Mueller is highly dedicated to his research on gentrification",
  "creation_timestamp": "2023-02-13T18:00:00Z",
  "last_access_timestamp": "2023-02-13T18:00:00Z",
  "importance_score": 8,
  "type": "reflection",
  "cited_memory_pointers": ["id_001", "id_002", "id_008", "id_015"]
}
```

### Tree Construction Algorithm

1. **Threshold Check** — sum(importance of recent memories) > 150 → initiate reflection
2. **Query Generation** — LLM generates 3 high-level questions from 100 most recent records
3. **Retrieval** — Use 3 questions as queries to retrieve relevant memories from entire stream
4. **Synthesis & Citation** — LLM generates 5 insights with explicit citations (memory indices)
5. **Tree Construction** — Store reflections in memory stream, citations = edges/pointers to parent nodes

### Tree Properties

| Property | Behavior |
|:---------|:---------|
| **Nodes** | Leaf nodes = raw observations; Non-leaf nodes = reflections |
| **Branching factor** | Dynamic — determined by how many records the LLM cites per insight (e.g., citing 4 records = 4 branches) |
| **Depth** | Grows recursively over time as newer reflections cite older ones |
| **Depth growth** | Each time a newer reflection cites an older reflection, the tree gains a new level |
| **No strict limits** | No predefined max depth or branching factor — purely emergent from LLM citations |

### How Higher-Level Abstractions Work

Reflections are **first-class memory objects** stored alongside observations in the memory stream. They are surfaced during normal retrieval. When the agent performs a new reflection, the LLM sees a mix of:
- Raw observations (leaf nodes)
- Past reflections (higher nodes)

By reflecting on older reflections, the agent recursively synthesizes **increasingly abstract thoughts** — the further up the tree, the more abstract.

---

## Key Properties

- Memory Stream is a **long-term, append-only database**
- Contains: **observations** (direct perception), **reflections** (abstract thought), **plans** (future actions)
- Too large for LLM context → retrieval algorithm surfaces relevant subset
- Retrieval happens **dynamically** whenever agent needs to act/react
