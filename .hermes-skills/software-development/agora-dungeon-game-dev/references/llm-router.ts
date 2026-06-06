// llm-router.ts
// LLM + Traditional AI Hybrid Router for Agora Dungeon
// Based on: Generative Agents + ReAct + Voyager papers

export enum TaskDomain {
    SOCIAL_DIALOGUE = "SOCIAL_DIALOGUE",
    HIGH_LEVEL_PLAN = "HIGH_LEVEL_PLAN",
    REFLECTION = "REFLECTION",
    PATHFINDING = "PATHFINDING",
    COMBAT_MOTOR = "COMBAT_MOTOR",
    PHYSICS = "PHYSICS"
}

export interface GameTask {
    id: string;
    description: string;
    domain: TaskDomain;
    context: Record<string, any>;
}

export interface TaskResult {
    executedBy: "LLM" | "TRADITIONAL" | "CACHE";
    output: any;
}

// ============================================================
// 1. LLM Cache (prevents repeated API calls)
// ============================================================

class LLMCache {
    private cache: Map<string, { result: any; timestamp: number }> = new Map();
    private readonly TTL_MS = 60000; // 1 minute TTL

    private generateKey(task: GameTask): string {
        return `${task.description}_${JSON.stringify(task.context)}`;
    }

    public get(task: GameTask): any | null {
        const key = this.generateKey(task);
        const record = this.cache.get(key);
        if (record && Date.now() - record.timestamp < this.TTL_MS) {
            return record.result;
        }
        return null;
    }

    public set(task: GameTask, result: any): void {
        const key = this.generateKey(task);
        this.cache.set(key, { result, timestamp: Date.now() });
    }
}

// ============================================================
// 2. Traditional Engine (fast, deterministic)
// ============================================================

class TraditionalEngine {
    public execute(task: GameTask): TaskResult {
        let output = "";
        switch (task.domain) {
            case TaskDomain.PATHFINDING:
                output = "A* Path: [Node A → Node B → Node C]";
                break;
            case TaskDomain.COMBAT_MOTOR:
                output = "BT: [Take Cover → Fire Weapon]";
                break;
            case TaskDomain.PHYSICS:
                output = "Physics: velocity updated";
                break;
        }
        return { executedBy: "TRADITIONAL", output };
    }
}

// ============================================================
// 3. LLM Engine (async, high-latency)
// ============================================================

class LLMEngine {
    public async execute(task: GameTask): Promise<TaskResult> {
        // Simulate 1.5s API latency
        await new Promise(r => setTimeout(r, 1500));

        let output = "";
        switch (task.domain) {
            case TaskDomain.SOCIAL_DIALOGUE:
                output = '"Hello there! I heard you were heading to the cafe."';
                break;
            case TaskDomain.HIGH_LEVEL_PLAN:
                output = "1. Find key. 2. Unlock door. 3. Retrieve artifact.";
                break;
            case TaskDomain.REFLECTION:
                output = "Insight: The player tends to attack from the shadows.";
                break;
        }
        return { executedBy: "LLM", output };
    }
}

// ============================================================
// 4. LLM Service with Async Queue (for tick loop)
// ============================================================

export interface LLMRequest {
    id: string;
    prompt: string;
    timeoutMs: number;
    fallbackResponse: string;
    resolve: (response: string) => void;
}

export class LLMService {
    private requestQueue: LLMRequest[] = [];
    private readonly MAX_CALLS_PER_TICK = 2;

    public enqueueRequest(prompt: string, timeoutMs: number, fallbackResponse: string): Promise<string> {
        return new Promise((resolve) => {
            this.requestQueue.push({
                id: Math.random().toString(36).substring(2, 9),
                prompt,
                timeoutMs,
                fallbackResponse,
                resolve
            });
        });
    }

    /** Call every frame in the game loop */
    public tick(): void {
        let callsThisTick = 0;
        while (this.requestQueue.length > 0 && callsThisTick < this.MAX_CALLS_PER_TICK) {
            const request = this.requestQueue.shift();
            if (request) { this.dispatchCall(request); callsThisTick++; }
        }
    }

    private async dispatchCall(request: LLMRequest): Promise<void> {
        try {
            const response = await Promise.race([
                this.mockNetworkCall(request.prompt),
                this.createTimeout(request.timeoutMs, request.fallbackResponse)
            ]);
            request.resolve(response);
        } catch {
            request.resolve(request.fallbackResponse);
        }
    }

    private createTimeout(ms: number, fallback: string): Promise<string> {
        return new Promise(resolve => setTimeout(() => resolve(fallback), ms));
    }

    private mockNetworkCall(prompt: string): Promise<string> {
        return new Promise(resolve => {
            const delay = Math.random() * 2500 + 500;
            setTimeout(() => resolve(`LLM: "${prompt}"`), delay);
        });
    }

    public get queueLength(): number { return this.requestQueue.length; }
}

export enum AgentState {
    IDLE = "IDLE",
    THINKING = "THINKING",
    ACTING = "ACTING"
}

export class LLMAgent {
    public state: AgentState = AgentState.IDLE;
    public latestIdea: string = "";

    constructor(public name: string, private llmService: LLMService) {}

    public tick(): void {
        switch (this.state) {
            case AgentState.IDLE:
                this.decideToThink();
                break;
            case AgentState.THINKING:
                break;
            case AgentState.ACTING:
                console.log(`[${this.name}] Executing: "${this.latestIdea}"`);
                this.state = AgentState.IDLE;
                break;
        }
    }

    private decideToThink(): void {
        this.state = AgentState.THINKING;
        this.llmService.enqueueRequest(
            "I see a locked door and a goblin. What should I do?",
            1500,
            "Fallback: Attack the goblin!"
        ).then(response => {
            this.latestIdea = response;
            this.state = AgentState.ACTING;
        });
    }
}

// ============================================================
// 5. Context Builder — assemble prompt from game world
// ============================================================

export interface WorldContext {
    agentName: string;
    location: string;
    health: number;
    inventory: string[];
    nearbyEntities: { name: string; type: string; relationship: string }[];
    recentMemories: string[];
    currentObjective: string;
}

export class ContextBuilder {
    public buildPrompt(ctx: WorldContext): string {
        const sections: string[] = [];

        sections.push(`You are ${ctx.agentName}. You are at ${ctx.location}.`);
        sections.push(`Health: ${ctx.health}/100. Inventory: ${ctx.inventory.join(', ') || 'empty'}.`);
        sections.push(`Current objective: ${ctx.currentObjective}`);

        if (ctx.recentMemories.length > 0) {
            const mems = ctx.recentMemories.slice(-5).map(m => `- ${m}`).join('\n');
            sections.push(`Recent memories:\n${mems}`);
        }

        const entities = ctx.nearbyEntities
            .map(e => `- ${e.name} (${e.type}, relationship: ${e.relationship})`)
            .join('\n');
        sections.push(`Nearby:\n${entities}`);

        sections.push(`\nWhat do you do? Respond with a short action.`);

        return sections.join('\n');
    }
}

// Example prompt for dungeon agent:
// You are Kael the Brave. You are at Forgotten Crypt, Room of Echoes.
// Health: 42/100. Inventory: Iron Sword, Rusty Key, Health Potion x3.
// Current objective: Find the Crystal of Eternity.
// Recent memories:
// - "Yesterday, Bob betrayed me during the dragon fight"
// - "I found the Rusty Key in the altar room"
// - "Lysandra healed me before the crypt entrance"
// Nearby:
// - Bob (NPC, relationship: betrayed you)
// - Lysandra (NPC, relationship: ally)
// - Stone Golem (monster, hostile)
// What do you do? Respond with a short action.


interface QueuedRequest {
    task: GameTask;
    resolve: (result: TaskResult) => void;
    reject: (err: Error) => void;
    timestamp: number;
}

export class LLMService {
    private queue: QueuedRequest[] = [];
    private processing: boolean = false;
    private llmEngine = new LLMEngine();
    private cache = new LLMCache();
    private traditionalEngine = new TraditionalEngine();

    private readonly MAX_CALLS_PER_TICK: number = 2;
    private readonly LLM_TIMEOUT_MS: number = 5000;

    /**
     * Queue an LLM task. Returns a Promise that resolves when done.
     * If cache hit → resolves instantly. If traditional → resolves sync.
     * Otherwise → queues for async processing.
     */
    public async enqueue(task: GameTask): Promise<TaskResult> {
        // Check if traditional domain
        if ([TaskDomain.PATHFINDING, TaskDomain.COMBAT_MOTOR, TaskDomain.PHYSICS].includes(task.domain)) {
            return this.traditionalEngine.execute(task);
        }

        // Check cache
        const cached = this.cache.get(task);
        if (cached) {
            return { executedBy: "CACHE", output: cached };
        }

        // Queue LLM request
        return new Promise((resolve, reject) => {
            this.queue.push({ task, resolve, reject, timestamp: Date.now() });
            this.processQueue();
        });
    }

    /**
     * Process the queue — called every tick or when new items arrive.
     * Respects rate limits and timeouts.
     */
    private async processQueue(): Promise<void> {
        if (this.processing) return;
        this.processing = true;

        while (this.queue.length > 0) {
            // Rate limit: max N concurrent calls
            const batch = this.queue.splice(0, this.MAX_CALLS_PER_TICK);

            await Promise.all(batch.map(async (req) => {
                try {
                    // Timeout race
                    const result = await Promise.race([
                        this.llmEngine.execute(req.task),
                        new Promise<never>((_, reject) =>
                            setTimeout(() => reject(new Error("LLM Timeout")), this.LLM_TIMEOUT_MS)
                        )
                    ]);

                    // Cache successful result
                    this.cache.set(req.task, result.output);
                    req.resolve(result);
                } catch (err) {
                    // Fallback: use traditional engine on timeout
                    console.warn(`[LLM Service] Timeout for '${req.task.description}', using fallback.`);
                    req.resolve({
                        executedBy: "TRADITIONAL",
                        output: `Fallback: ${req.task.description}`
                    });
                }
            }));
        }

        this.processing = false;
    }

    public get queueLength(): number {
        return this.queue.length;
    }
}

// ============================================================
// 5. Decision Flow: "Which way to go?"
// ============================================================

/**
 * [Incoming Game Event]
 *        ↓
 * Is it abstract, conversational, or socially complex?
 *   ├── YES → LLM Route
 *   │         ├── Needs memory? → Query Memory Stream
 *   │         ├── Generate Dialogue / Plan / Reflection
 *   │         └── Output: speech or abstract goals
 *   └── NO
 *        ↓
 * Does it need real-time spatial movement, physics, or combat?
 *   ├── YES → Traditional Route
 *   │         ├── Pathfinding? → A* / NavMesh
 *   │         ├── Combat? → BT / Utility AI
 *   │         └── Output: velocity, animation, motor control
 *   └── NO
 *        ↓
 * Is this translating high-level plan to actions?
 *   └── YES → Hybrid Route (LLM plan → Traditional execute)
 *              LLM: "Go to cafe" → A* executes the route
 */

// ============================================================
// 6. Example Usage
// ============================================================

/*
const router = new LLMRouter();

// Traditional — fast, no LLM
await router.enqueue({
    id: "T1",
    description: "Move from (10,15) to (30,45)",
    domain: TaskDomain.PATHFINDING,
    context: {}
});

// LLM — async, with queue
await router.enqueue({
    id: "T2",
    description: "Greet the player approaching the shop",
    domain: TaskDomain.SOCIAL_DIALOGUE,
    context: { npcMood: "happy" }
});

// Cache hit — returns instantly
await router.enqueue({
    id: "T2",
    description: "Greet the player approaching the shop",
    domain: TaskDomain.SOCIAL_DIALOGUE,
    context: { npcMood: "happy" }
});

// Combat — traditional BT
await router.enqueue({
    id: "T4",
    description: "Player threw a grenade",
    domain: TaskDomain.COMBAT_MOTOR,
    context: { threatType: "explosive", distance: 2.5 }
});
*/
