// types.ts
export type MemoryType = "observation" | "reflection" | "plan";

export interface Memory {
    id: string;
    description: string;
    creation_timestamp: number; // Represented in simulated hours
    last_access_timestamp: number; // Represented in simulated hours
    importance_score: number; // 1 to 10
    type: MemoryType;
    embedding: number[];
}

// mockEmbedding.ts
// A simple mock interface for text embeddings (e.g., OpenAI text-embedding-ada-002)
export function getMockEmbedding(text: string): number[] {
    // In production, call your LLM embedding API here
    return Array.from({ length: 1536 }, () => Math.random());
}

export function cosineSimilarity(vecA: number[], vecB: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < vecA.length; i++) {
        dotProduct += vecA[i] * vecB[i];
        normA += vecA[i] * vecA[i];
        normB += vecB[i] * vecB[i];
    }
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB) || 1);
}

// mathUtils.ts
// Normalizes a value to a 0-1 range using min-max scaling
export function normalize(value: number, min: number, max: number): number {
    if (max === min) return 0; // Prevent division by zero
    return (value - min) / (max - min);
}

// GenerativeAgent.ts
export class GenerativeAgent {
    private memoryStream: Memory[] = [];
    private unreflectedImportance: number = 0;
    public currentTime: number = 0; // Elapsed time in the simulation (e.g., hours)
    
    // Decay rate γ defined in the architecture
    private readonly DECAY_RATE: number = 0.995;
    private readonly REFLECTION_THRESHOLD: number = 150;

    constructor(public name: string) {}

    /**
     * Appends a new memory to the Memory Stream and triggers reflection if necessary.
     */
    public appendMemory(description: string, importance: number, type: MemoryType): void {
        const memory: Memory = {
            id: Math.random().toString(36).substring(2, 9),
            description,
            creation_timestamp: this.currentTime,
            last_access_timestamp: this.currentTime,
            importance_score: importance,
            type,
            embedding: getMockEmbedding(description)
        };

        this.memoryStream.push(memory);
        this.unreflectedImportance += importance;

        // Reflection Trigger (sum importance > 150)
        if (this.unreflectedImportance > this.REFLECTION_THRESHOLD) {
            this.triggerReflection();
        }
    }

    /**
     * Retrieves the top K memories using: recency × importance × relevance weighting.
     * All alpha weights are strictly set to 1.
     */
    public retrieve(query: string, topK: number): Memory[] {
        if (this.memoryStream.length === 0) return [];

        const queryEmbedding = getMockEmbedding(query);

        // 1. Calculate raw scores for all memories
        const rawScores = this.memoryStream.map(mem => {
            // Recency: Exponential decay d(e) = 0.995^t
            const timeElapsed = this.currentTime - mem.last_access_timestamp;
            const recency = Math.pow(this.DECAY_RATE, timeElapsed);
            
            // Relevance: Cosine similarity
            const relevance = cosineSimilarity(queryEmbedding, mem.embedding);
            
            // Importance: Raw 1-10 score
            const importance = mem.importance_score;
            return { mem, recency, relevance, importance };
        });

        // 2. Find min and max for Min-Max Scaling
        const minRec = Math.min(...rawScores.map(s => s.recency));
        const maxRec = Math.max(...rawScores.map(s => s.recency));
        
        const minRel = Math.min(...rawScores.map(s => s.relevance));
        const maxRel = Math.max(...rawScores.map(s => s.relevance));
        
        const minImp = Math.min(...rawScores.map(s => s.importance));
        const maxImp = Math.max(...rawScores.map(s => s.importance));

        // 3. Normalize and combine (Score = Recency + Importance + Relevance)
        const finalScores = rawScores.map(s => {
            const normRecency = normalize(s.recency, minRec, maxRec);
            const normRelevance = normalize(s.relevance, minRel, maxRel);
            const normImportance = normalize(s.importance, minImp, maxImp);
            
            // Final Retrieval Score Formula
            const totalScore = normRecency + normImportance + normRelevance;
            
            return { memory: s.mem, totalScore };
        });

        // 4. Sort descending by total score and slice Top K
        finalScores.sort((a, b) => b.totalScore - a.totalScore);
        const retrievedMemories = finalScores.slice(0, topK).map(res => res.memory);

        // 5. Update last access timestamp for retrieved memories
        retrievedMemories.forEach(mem => {
            mem.last_access_timestamp = this.currentTime;
        });

        return retrievedMemories;
    }

    /**
     * Synthesizes higher-level thoughts from recent memories.
     */
    private triggerReflection(): void {
        console.log(`[Reflection Triggered] Unreflected importance reached ${this.unreflectedImportance}.`);
        
        // In production, prompt the LLM to generate 3 questions, retrieve relevant memories, 
        // and synthesize 5 high-level insights based on the retrieved subset.
        const mockInsight = `${this.name} reflects on recent recurring themes in their environment.`;
        
        // Append reflection back into the memory stream as a first-class object
        this.appendMemory(mockInsight, 8, "reflection");
        
        // Reset the threshold counter
        this.unreflectedImportance = 0;
    }

    /**
     * Recursive Planning: Daily -> Hourly -> Micro-Actions
     */
    public generatePlan(context: string): void {
        console.log("[Planning] Generating daily agenda...");
        // Prompt LLM for broad strokes
        const dailyPlan = "Work on research paper from 9am to 5pm.";
        this.appendMemory(`Daily Plan: ${dailyPlan}`, 7, "plan");

        console.log("[Planning] Decomposing into hourly chunks...");
        // Prompt LLM to recursively decompose
        const hourlyPlan = "1:00pm: brainstorm. 2:00pm: write draft.";
        this.appendMemory(`Hourly Plan: ${hourlyPlan}`, 5, "plan");

        console.log("[Planning] Decomposing into micro-actions...");
        // Prompt LLM for 5-15 minute actions
        const microAction = "1:00pm - 1:15pm: gather notes on desk.";
        this.appendMemory(`Micro-Action: ${microAction}`, 3, "plan");
    }

    /**
     * ReAct Loop: Perceive -> Decide (Reason) -> Act
     */
    public reactLoop(observation: string): void {
        console.log(`\n[Perceive] Observation: ${observation}`);
        this.appendMemory(`Observed: ${observation}`, 5, "observation");

        // Step 1: Retrieve context to aid decision making
        const relevantContext = this.retrieve(observation, 5);
        const contextDescriptions = relevantContext.map(m => m.description).join(" | ");

        // Step 2: Decide (Reasoning Trace)
        console.log("[Decide] Generating reasoning trace...");
        const reasoningTrace = `Thought: Based on seeing '${observation}' and knowing '${contextDescriptions}', I should adapt my plan.`;
        console.log(reasoningTrace);
        
        // Step 3: Act
        console.log("[Act] Executing action...");
        const action = `Action: Stop current task and address '${observation}'.`;
        console.log(action);
        
        // Advance time
        this.currentTime += 0.25; 
    }
}

// --- Example Usage ---
const agent = new GenerativeAgent("Klaus Mueller");

// Adding base memories
agent.appendMemory("Klaus is reading a book on gentrification", 4, "observation");
agent.appendMemory("Klaus is highly dedicated to his research", 8, "reflection");
agent.appendMemory("Klaus wakes up at 7:00 AM", 2, "observation");

// Advance time to test decay
agent.currentTime = 5; 

// Run ReAct loop
agent.reactLoop("Ayesha Khan walks into the library and waves.");
