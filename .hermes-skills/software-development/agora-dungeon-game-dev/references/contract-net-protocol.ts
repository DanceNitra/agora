// contract-net-protocol.ts
// Contract Net Protocol (CNP) for Agora multi-agent coordination
// Based on: Shoham & Leyton-Brown "Multiagent Systems"

// ============================================================
// 1. Types & Interfaces
// ============================================================

export interface Task {
    id: string;
    name: string;
    requiredCapabilities: string[];
    location?: { x: number; y: number };
    reward?: number;
    deadline?: number; // game time by which task must be done
}

export interface Bid {
    agentId: string;
    taskId: string;
    marginalCost: number;
    estimatedTime: number; // game ticks to complete
}

// ============================================================
// 2. Contractor Agent (Bidder / Executor)
// ============================================================

export class ContractorAgent {
    public currentTasks: Task[] = [];
    public totalCostIncurred: number = 0;

    constructor(
        public id: string,
        public capabilities: string[],
        public efficiency: number = 1.0 // lower = better (1.0 normal, 0.5 super-fast)
    ) {}

    /**
     * Evaluate task and return a Bid if capable.
     */
    public evaluateTask(task: Task): Bid | null {
        // Check capabilities
        const isCapable = task.requiredCapabilities.every(cap =>
            this.capabilities.includes(cap)
        );
        if (!isCapable) return null;

        const cost = this.calculateMarginalCost(task);
        const time = this.estimateTime(task);

        return { agentId: this.id, taskId: task.id, marginalCost: cost, estimatedTime: time };
    }

    /**
     * Marginal cost = baseCost + workloadPenalty − efficiencyBonus
     * c_i(T ∪ {task}) − c_i(T)
     */
    private calculateMarginalCost(task: Task): number {
        const baseCost = 10;
        const workloadPenalty = this.currentTasks.length * 5;
        const efficiencyBonus = (1 - this.efficiency) * 10;
        const noise = Math.random() * 3;
        return baseCost + workloadPenalty - efficiencyBonus + noise;
    }

    /**
     * Estimate time in game ticks
     */
    private estimateTime(task: Task): number {
        const base = 5;
        const complexity = task.requiredCapabilities.length * 2;
        return Math.ceil((base + complexity) * this.efficiency);
    }

    /**
     * Execute task async
     */
    public async executeTask(task: Task): Promise<void> {
        this.currentTasks.push(task);
        this.totalCostIncurred += this.calculateMarginalCost(task);
        console.log(`[${this.id}] Executing: ${task.name}...`);

        // Simulate work duration
        const duration = this.estimateTime(task) * 300; // ms
        return new Promise(resolve => {
            setTimeout(() => {
                this.currentTasks = this.currentTasks.filter(t => t.id !== task.id);
                console.log(`[${this.id}] Completed: ${task.name}`);
                resolve();
            }, Math.min(duration, 3000));
        });
    }
}

// ============================================================
// 3. Manager Agent (Announcer / Awarder)
// ============================================================

export class ManagerAgent {
    private completedTasks: number = 0;
    private failedTasks: number = 0;

    constructor(private knownAgents: ContractorAgent[]) {}

    /**
     * Full CNP lifecycle: Announce → Bid → Award → Execute → Confirm
     */
    public async processTask(task: Task): Promise<boolean> {
        console.log(`\n[Manager] ANNOUNCE: ${task.name} (needs: ${task.requiredCapabilities.join(', ')})`);

        // Step 2: Collect bids
        const bids: Bid[] = [];
        for (const agent of this.knownAgents) {
            const bid = agent.evaluateTask(task);
            if (bid) bids.push(bid);
        }

        // Step 3: Award to lowest bidder
        if (bids.length === 0) {
            console.log(`[Manager] FAILED: No bids for '${task.name}'`);
            this.failedTasks++;
            return false;
        }

        bids.sort((a, b) => a.marginalCost - b.marginalCost);
        const winner = bids[0];
        const agent = this.knownAgents.find(a => a.id === winner.agentId)!;

        console.log(`[Manager] AWARD → ${winner.agentId} (cost: ${winner.marginalCost.toFixed(1)}, time: ${winner.estimatedTime}t)`);

        // Step 4-5: Execute & confirm
        await agent.executeTask(task);
        console.log(`[Manager] CONFIRMED: '${task.name}' by ${agent.id}`);
        this.completedTasks++;
        return true;
    }

    get stats(): string {
        return `✅ ${this.completedTasks} completed, ❌ ${this.failedTasks} failed`;
    }
}

// ============================================================
// 4. Vickrey (Second-Price) Auction for task allocation
// ============================================================

export class VickreyAuction {
    constructor(private agents: ContractorAgent[]) {}

    /**
     * Vickrey auction: highest bidder wins, pays second-highest price.
     * Used when multiple agents want the SAME scarce task.
     */
    public async auctionTask(task: Task): Promise<void> {
        console.log(`\n[Vickrey] AUCTION: ${task.name}`);

        // Collect bids (valuation = negative cost — higher is better)
        interface Valuation { agentId: string; value: number; bid: Bid; }
        const valuations: Valuation[] = [];

        for (const agent of this.agents) {
            const bid = agent.evaluateTask(task);
            if (bid) {
                valuations.push({
                    agentId: agent.id,
                    value: -bid.marginalCost, // willingness to accept payment
                    bid
                });
            }
        }

        if (valuations.length < 2) {
            console.log(`[Vickrey] Not enough bidders (${valuations.length})`);
            return;
        }

        // Sort by value descending
        valuations.sort((a, b) => b.value - a.value);
        const winner = valuations[0];
        const secondPrice = valuations[1].bid.marginalCost;

        console.log(`[Vickrey] WINNER: ${winner.agentId} pays ${secondPrice.toFixed(1)}`);
        const agent = this.agents.find(a => a.id === winner.agentId)!;
        await agent.executeTask(task);
    }
}

// ============================================================
// 5. Example Usage
// ============================================================

/*
const worker1 = new ContractorAgent("Grom", ["combat", "heavy_lifting"], 0.8);
const worker2 = new ContractorAgent("Zara", ["scouting", "repair"], 1.2);
const worker3 = new ContractorAgent("Finn", ["combat", "scouting", "movement"], 1.0);

const manager = new ManagerAgent([worker1, worker2, worker3]);

// Dungeon tasks
const tasks: Task[] = [
    { id: "t1", name: "Clear Goblin Nest", requiredCapabilities: ["combat"] },
    { id: "t2", name: "Fix Portcullis", requiredCapabilities: ["repair", "heavy_lifting"] },
    { id: "t3", name: "Scout North Corridor", requiredCapabilities: ["scouting", "movement"] },
];

(async () => {
    for (const task of tasks) {
        await manager.processTask(task);
    }
    console.log(manager.stats);
})();
*/
