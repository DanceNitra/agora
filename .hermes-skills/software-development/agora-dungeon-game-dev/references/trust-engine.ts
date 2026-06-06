// trust-engine.ts
// Trust and Reputation system for multi-agent coordination
// Based on: Shoham & Leyton-Brown "Multiagent Systems"

export interface InteractionResult {
    partnerId: string;
    success: boolean;
}

export class TrustEngine {
    private trustScores: Map<string, number> = new Map();

    constructor(
        public initialTrust: number = 0.5,
        public threshold: number = 0.4,
        public decayRate: number = 0.98,
        public forgiveness: number = 0.05,
        public learningRate: number = 0.2
    ) {}

    updateTrust(result: InteractionResult): void {
        let trust = this.getTrust(result.partnerId);
        trust *= this.decayRate;

        if (result.success) {
            trust = trust + this.learningRate * (1.0 - trust);
        } else {
            trust = trust - this.learningRate * trust + this.forgiveness;
        }

        trust = Math.max(0.0, Math.min(1.0, trust));
        this.trustScores.set(result.partnerId, trust);
    }

    selectTrustedPartners(availableAgents: string[]): string[] {
        const eligible = availableAgents.filter(id => this.getTrust(id) >= this.threshold);
        return eligible.sort((a, b) => this.getTrust(b) - this.getTrust(a));
    }

    getTrust(agentId: string): number {
        return this.trustScores.get(agentId) ?? this.initialTrust;
    }

    applyGlobalDecay(): void {
        for (const [id, score] of this.trustScores.entries()) {
            this.trustScores.set(id, Math.max(0.0, score * this.decayRate));
        }
    }
}

export function selectPartnerWithTrust(
    bids: { agentId: string; marginalCost: number }[],
    trustEngine: TrustEngine
): string | null {
    if (bids.length === 0) return null;
    const trusted = bids.filter(b => trustEngine.getTrust(b.agentId) >= trustEngine.threshold);
    if (trusted.length === 0) return null;
    trusted.sort((a, b) => a.marginalCost - b.marginalCost);
    return trusted[0].agentId;
}
