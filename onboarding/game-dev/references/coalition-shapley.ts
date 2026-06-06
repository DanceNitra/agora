// coalition-shapley.ts
// Coalition Formation and Shapley Value for fair reward distribution
// Based on: Shoham & Leyton-Brown "Multiagent Systems"

export type Coalition = string[];
export type CharacteristicFunction = (coalition: Coalition) => number;

function factorial(n: number): number {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

function getSubsets(arr: string[]): string[][] {
    return arr.reduce(
        (subsets, value) => subsets.concat(subsets.map(set => [value, ...set])),
        [[]] as string[][]
    );
}

// ============================================================
// Coalitional Game Engine
// ============================================================

export class CoalitionalGame {
    constructor(
        public agents: string[],
        public v: CharacteristicFunction
    ) {}

    /**
     * Shapley Value: φ_i(v) = Σ [|S|!(|N|-|S|-1)! / |N|!] * [v(S∪{i}) - v(S)]
     * Fair distribution of grand coalition's payoff.
     */
    public calculateShapleyValues(): Record<string, number> {
        const values: Record<string, number> = {};
        const N = this.agents.length;
        const factN = factorial(N);

        for (const i of this.agents) {
            values[i] = 0;
            const others = this.agents.filter(a => a !== i);
            const subsets = getSubsets(others);

            for (const S of subsets) {
                const weight = (factorial(S.length) * factorial(N - S.length - 1)) / factN;
                const marginal = this.v([...S, i]) - this.v(S);
                values[i] += weight * marginal;
            }
        }

        return values;
    }

    /**
     * Check if game is superadditive:
     * v(S ∪ T) ≥ v(S) + v(T) for all disjoint S, T
     */
    public isSuperadditive(): boolean {
        const subsets = getSubsets(this.agents);
        for (const S of subsets) {
            const remaining = this.agents.filter(a => !S.includes(a));
            const Tsubsets = getSubsets(remaining);
            for (const T of Tsubsets) {
                if (T.length === 0) continue;
                const combined = this.v([...S, ...T]);
                const separate = this.v(S) + this.v(T);
                if (combined < separate) return false;
            }
        }
        return true;
    }
}

// ============================================================
// Dungeon Example: Reward Distribution for quest completion
// ============================================================

// In a dungeon, agents complete a quest together.
// Each agent brings different value (combat, scouting, healing).
// The quest reward is 100 gold.

export function dungeonRewardExample() {
    const agents = ["Grom", "Zara", "Finn"];
    
    // Characteristic function based on capabilities
    const questReward: CharacteristicFunction = (coalition) => {
        let value = 0;
        
        // Combat (Grom)
        if (coalition.includes("Grom")) value += 40;
        // Scouting (Zara)
        if (coalition.includes("Zara")) value += 25;
        // Healing (Finn)
        if (coalition.includes("Finn")) value += 15;
        
        // Synergy bonuses for combinations
        if (coalition.includes("Grom") && coalition.includes("Zara")) value += 10;
        if (coalition.includes("Zara") && coalition.includes("Finn")) value += 5;
        if (coalition.includes("Grom") && coalition.includes("Finn")) value += 5;
        
        // Grand coalition bonus (all three together)
        if (coalition.length === 3) value += 10;
        
        return value;
    };

    const game = new CoalitionalGame(agents, questReward);
    const distribution = game.calculateShapleyValues();
    
    console.log("🏆 Quest Reward Distribution:");
    for (const [agent, reward] of Object.entries(distribution)) {
        console.log(`  ${agent}: ${reward.toFixed(1)} gold`);
    }
    
    console.log(`\nTotal distributed: ${Object.values(distribution).reduce((a, b) => a + b, 0).toFixed(1)} / ${questReward(agents)} gold`);
    console.log(`Superadditive: ${game.isSuperadditive()}`);
}

// ============================================================
// Example: Parliament Voting Game
// ============================================================

export function parliamentExample() {
    const votes: Record<string, number> = { A: 45, B: 25, C: 15, D: 15 };
    const totalVotes = Object.values(votes).reduce((a, b) => a + b, 0);
    const majority = Math.floor(totalVotes / 2) + 1; // 51

    const billFunction: CharacteristicFunction = (coalition) => {
        const sum = coalition.reduce((s, p) => s + votes[p], 0);
        return sum >= majority ? 100 : 0;
    };

    const game = new CoalitionalGame(["A", "B", "C", "D"], billFunction);
    const distribution = game.calculateShapleyValues();

    console.log("💵 Parliament Bill ($100M):");
    for (const [party, reward] of Object.entries(distribution)) {
        console.log(`  Party ${party} (${votes[party]} votes): $${reward.toFixed(2)}M`);
    }
    // A: $50M, B: $16.67M, C: $16.67M, D: $16.67M
    // Even though A has 45 votes, they get 50% — because A needs exactly 1 partner to pass
}
