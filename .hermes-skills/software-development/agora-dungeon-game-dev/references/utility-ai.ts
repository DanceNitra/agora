// utility-ai.ts
// Utility AI system for Agora Dungeon NPC decisions
// Based on: Buckland "Programming Game AI by Example" + Millington "AI for Games"

// ============================================================
// 1. Utility Curves
// ============================================================

export const UtilityCurves = {
    linear: (x: number): number => x,

    /** Exponential: low values stay low, high values spike. */
    exponential: (x: number, exponent: number = 2): number => Math.pow(x, exponent),

    /** Logistic (S-Curve): stays low until midpoint, then spikes to 1. */
    logistic: (x: number, steepness: number = 10, midpoint: number = 0.5): number => {
        return 1 / (1 + Math.exp(-steepness * (x - midpoint)));
    },

    /** Quadratic: flips the curve — high values stay low, only extreme low spikes. */
    quadratic: (x: number): number => 1 - Math.pow(1 - x, 2),
};

// ============================================================
// 2. BT Runtime (minimal)
// ============================================================

export enum NodeState {
    SUCCESS = "SUCCESS",
    FAILURE = "FAILURE",
    RUNNING = "RUNNING"
}

export interface NPCContext {
    health: number;
    distanceToEnemy: number;
    hasPotion: boolean;
    stamina: number;
    hunger: number;
}

export abstract class BTNode {
    abstract tick(ctx: NPCContext): NodeState;
}

// ============================================================
// 3. Utility Action — leaf node with scoring
// ============================================================

export class UtilityAction extends BTNode {
    constructor(
        public name: string,
        private utilityFn: (ctx: NPCContext) => number,
        private actionFn: (ctx: NPCContext) => NodeState
    ) {
        super();
    }

    getUtility(ctx: NPCContext): number {
        return Math.max(0, Math.min(1, this.utilityFn(ctx)));
    }

    tick(ctx: NPCContext): NodeState {
        console.log(`  ▶ ${this.name}`);
        return this.actionFn(ctx);
    }
}

// ============================================================
// 4. Utility Fallback — dynamic priority selector
// ============================================================

export class UtilityFallback extends BTNode {
    constructor(public children: UtilityAction[]) {
        super();
    }

    tick(ctx: NPCContext): NodeState {
        if (this.children.length === 0) return NodeState.FAILURE;

        // Score and sort all children by utility descending
        const scored = this.children
            .map(c => ({ node: c, score: c.getUtility(ctx) }))
            .sort((a, b) => b.score - a.score);

        const best = scored[0];
        console.log(`[Utility] Best: '${best.node.name}' (${best.score.toFixed(2)})`);

        // Try from highest to lowest (fallback on failure)
        for (const child of scored) {
            const status = child.node.tick(ctx);
            if (status !== NodeState.FAILURE) return status;
        }

        return NodeState.FAILURE;
    }
}

// ============================================================
// 5. Dungeon NPC Example
// ============================================================

export function createDungeonNPCBrain(): UtilityFallback {
    const normalize = (val: number, min: number, max: number) =>
        Math.max(0, Math.min(1, (val - min) / (max - min)));

    const heal = new UtilityAction(
        "Drink Potion",
        (ctx) => {
            if (!ctx.hasPotion) return 0;
            const danger = 1 - normalize(ctx.health, 0, 100);
            return UtilityCurves.exponential(danger, 3);
        },
        (ctx) => {
            ctx.health = 100;
            ctx.hasPotion = false;
            console.log("    💚 Healed to full!");
            return NodeState.SUCCESS;
        }
    );

    const attack = new UtilityAction(
        "Attack Enemy",
        (ctx) => {
            const proximity = 1 - normalize(ctx.distanceToEnemy, 0, 30);
            return UtilityCurves.logistic(proximity, 12, 0.6);
        },
        () => {
            console.log("    ⚔️  Attacking!");
            return NodeState.RUNNING;
        }
    );

    const flee = new UtilityAction(
        "Flee",
        (ctx) => {
            const danger = 1 - normalize(ctx.health, 0, 100);
            const proximity = 1 - normalize(ctx.distanceToEnemy, 0, 40);
            return (danger > 0.7 && proximity > 0.5) ? 0.9 : 0.1;
        },
        (ctx) => {
            ctx.distanceToEnemy += 10;
            console.log("    🏃 Fleeing!");
            return NodeState.SUCCESS;
        }
    );

    const patrol = new UtilityAction(
        "Patrol",
        () => 0.2, // default low-priority action
        () => {
            console.log("    🚶 Patrolling...");
            return NodeState.RUNNING;
        }
    );

    return new UtilityFallback([heal, attack, flee, patrol]);
}

// ============================================================
// 6. Test Simulation
// ============================================================

/*
const npc = {
    health: 100,
    distanceToEnemy: 50,
    hasPotion: true,
    stamina: 100,
    hunger: 0
};

const brain = createDungeonNPCBrain();

// Tick 1 — full health, no enemies → Patrol
brain.tick(npc);

// Tick 2 — enemy close → Attack
npc.distanceToEnemy = 5;
brain.tick(npc);

// Tick 3 — critical health → Heal
npc.health = 15;
brain.tick(npc);

// Tick 4 — no potion left, low health → Flee
npc.hasPotion = false;
brain.tick(npc);
*/
