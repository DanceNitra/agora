import Phaser from 'phaser';
import { BTState, BTNode, BTAction, BTCondition, BTSequence, BTSelector } from './BT';

const API_BASE = 'http://localhost:8000/api/v1/dungeon';

interface LLMDecision {
  action: string;
  target_x?: number;
  target_y?: number;
  target_npc?: string;
  message?: string;
  thought?: string;
}

/**
 * LLMNPCSprite — NPC that calls the Python backend LLM each tick.
 * Uses a simple BT wrapper to manage the async request cycle:
 *   IDLE → THINKING (call API) → ACTING (execute decision)
 */
export class LLMNPCSprite extends Phaser.Physics.Arcade.Sprite {
  private tree!: BTNode;
  private label!: Phaser.GameObjects.Text;
  private speechBubble!: Phaser.GameObjects.Text;

  private pendingDecision: LLMDecision | null = null;
  private thinkingTimer: number = 0;
  private isWaiting: boolean = false;
  private lastCallTime: number = 0;
  private readonly CALL_COOLDOWN = 3000; // ms between LLM calls

  // NPC state to send to backend
  public inventory: string[] = ['Rusty Key'];
  public health: number = 100;
  public currentObjective: string = 'Find the Crystal of Eternity';
  public nearbyNPCs: { name: string; role: string; x: number; y: number }[] = [];
  public memory: string[] = [];

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    name: string,
    public playerRef: Phaser.GameObjects.Sprite | null = null
  ) {
    super(scene, x, y, 'npc');
    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.setTint(0x44aaff); // Blue tint = LLM-powered
    this.setScale(1.3);

    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setCollideWorldBounds(true);
    body.setSize(20, 20);

    this.label = scene.add.text(x, y - 22, `${name} (LLM)`, {
      fontSize: '9px',
      color: '#aaddff',
      backgroundColor: '#00000088',
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5).setDepth(10);

    this.speechBubble = scene.add.text(x, y - 36, '', {
      fontSize: '8px',
      color: '#ffffff',
      backgroundColor: '#000000aa',
      padding: { x: 3, y: 2 },
      wordWrap: { width: 120 },
    }).setOrigin(0.5).setDepth(10).setAlpha(0);

    this.buildTree();
  }

  private buildTree(): void {
    this.tree = new BTSelector([
      // Priority 1: If we have a pending action, execute it
      this.makeSeq("Execute decision", [
        new BTCondition("Has decision?", () => this.pendingDecision !== null),
        new BTAction("Act", () => this.executeDecision()),
      ]),
      // Priority 2: If cooldown passed, think (call LLM)
      this.makeSeq("Think", [
        new BTCondition("Can think?", () => {
          const now = Date.now();
          return !this.isWaiting && (now - this.lastCallTime) > this.CALL_COOLDOWN;
        }),
        new BTAction("Call LLM", () => {
          this.isWaiting = true;
          this.lastCallTime = Date.now();
          this.callLLM();
          return BTState.RUNNING;
        }),
      ]),
      // Priority 3: Default idle
      new BTAction("Idle", () => {
        this.setVelocity(0, 0);
        return BTState.RUNNING;
      }),
    ]);
  }

  private makeSeq(name: string, children: BTNode[]): BTNode {
    return new BTSequence(children);
  }

  private async callLLM(): Promise<void> {
    this.label.setText(`${this.texture.key === 'npc' ? 'Kael' : 'Agent'}: thinking...`);

    try {
      const nearbyNPCs = this.nearbyNPCs.map(n => ({
        name: n.name, role: n.role, x: n.x, y: n.y,
      }));

      const body = JSON.stringify({
        agent_name: 'Kael',
        agent_x: this.x,
        agent_y: this.y,
        health: this.health,
        inventory: this.inventory,
        nearby_npcs: nearbyNPCs,
        nearby_objects: [
          { name: 'Anvil', x: 112, y: 448 },
          { name: 'Cauldron', x: 640, y: 96 },
          { name: 'Counter', x: 112, y: 112 },
        ],
        recent_memories: this.memory.slice(-5),
        current_objective: this.currentObjective,
      });

      const response = await fetch(`${API_BASE}/agent-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const decision: LLMDecision = await response.json();
      this.pendingDecision = decision;

      // Store memory
      if (decision.thought) {
        this.memory.push(decision.thought);
        if (this.memory.length > 20) this.memory.shift();
      }

      // Show speech bubble
      if (decision.message) {
        this.speechBubble.setText(`"${decision.message}"`);
        this.speechBubble.setAlpha(1);
        this.scene.time.delayedCall(3000, () => {
          this.speechBubble.setAlpha(0);
        });
      }

    } catch (err) {
      console.warn('[LLM NPC] API call failed, using fallback:', err);
      this.pendingDecision = {
        action: 'move',
        target_x: this.x + (Math.random() - 0.5) * 100,
        target_y: this.y + (Math.random() - 0.5) * 100,
        message: 'Hmm, let me check this out.',
        thought: 'Exploring randomly due to connection issues.',
      };
    }

    this.isWaiting = false;
  }

  private executeDecision(): BTState {
    if (!this.pendingDecision) return BTState.FAILURE;

    const d = this.pendingDecision;

    // Update label
    this.label.setText(`Kael:${d.action}`);

    switch (d.action) {
      case 'move':
      case 'explore': {
        const tx = d.target_x ?? this.x + 50;
        const ty = d.target_y ?? this.y;
        const dist = Phaser.Math.Distance.Between(this.x, this.y, tx, ty);
        if (dist < 10) {
          this.pendingDecision = null;
          this.setVelocity(0, 0);
          return BTState.SUCCESS;
        }
        const angle = Phaser.Math.Angle.Between(this.x, this.y, tx, ty);
        this.setVelocity(Math.cos(angle) * 60, Math.sin(angle) * 60);
        return BTState.RUNNING;
      }
      case 'interact':
        this.setVelocity(0, 0);
        this.pendingDecision = null;
        return BTState.SUCCESS;
      case 'wait':
        this.setVelocity(0, 0);
        this.thinkingTimer++;
        if (this.thinkingTimer > 60) {
          this.thinkingTimer = 0;
          this.pendingDecision = null;
          return BTState.SUCCESS;
        }
        return BTState.RUNNING;
      default:
        this.pendingDecision = null;
        this.setVelocity(0, 0);
        return BTState.SUCCESS;
    }
  }

  update(delta: number): void {
    this.tree.tick();

    // Update labels
    this.label.setPosition(this.x, this.y - 22);
    this.speechBubble.setPosition(this.x, this.y - 40);
    this.setDepth(this.y);
    this.label.setDepth(this.y + 1);
    this.speechBubble.setDepth(this.y + 1);
  }

  destroy() {
    this.label?.destroy();
    this.speechBubble?.destroy();
    super.destroy();
  }
}
