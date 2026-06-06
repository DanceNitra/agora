/**
 * NPC FSM — lightweight state machine for Phaser NPC behavior.
 * Phased 1: idle, wander, work states.
 * Based on: Buckland "Programming Game AI by Example"
 */

export const NPCStateNames = ['idle', 'wander', 'work'] as const;
export type NPCState = (typeof NPCStateNames)[number];

/** Transition condition: from state → to state when condition is met */
interface Transition {
  from: NPCState;
  to: NPCState;
  condition: () => boolean;
}

export class NPCBrain {
  public currentState: NPCState = 'idle';
  private stateTimer: number = 0; // ticks spent in current state
  private transitions: Transition[] = [];

  constructor(
    public npc: {
      name: string;
      idle(): void;
      wander(): void;
      work(): void;
      getBoredom(): number;
      hasWork(): boolean;
    }
  ) {
    this.setupTransitions();
  }

  private setupTransitions(): void {
    // idle → wander when bored
    this.addTransition('idle', 'wander', () => this.npc.getBoredom() > 5);
    // wander → idle when no longer bored
    this.addTransition('wander', 'idle', () => this.npc.getBoredom() <= 0);
    // idle → work if has work to do
    this.addTransition('idle', 'work', () => this.npc.hasWork() && this.stateTimer > 3);
    // work → idle when done
    this.addTransition('work', 'idle', () => this.stateTimer > 8);
    // wander → work if has work and wandered enough
    this.addTransition('wander', 'work', () => this.npc.hasWork() && this.stateTimer > 5);
  }

  addTransition(from: NPCState, to: NPCState, condition: () => boolean): void {
    this.transitions.push({ from, to, condition });
  }

  /** Call every game tick (called from Phaser update) */
  update(): void {
    this.stateTimer++;

    // Check transitions
    for (const t of this.transitions) {
      if (t.from === this.currentState && t.condition()) {
        this.currentState = t.to;
        this.stateTimer = 0;
        break;
      }
    }

    // Execute current state
    switch (this.currentState) {
      case 'idle':
        this.npc.idle();
        break;
      case 'wander':
        this.npc.wander();
        break;
      case 'work':
        this.npc.work();
        break;
    }
  }

  resetTimer(): void {
    this.stateTimer = 0;
  }
}
