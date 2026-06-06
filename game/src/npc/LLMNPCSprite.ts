/**
 * LLMNPCSprite — NPC with A* navigation, action queuing, and persistent memory.
 *
 * Behavior Tree (priority):
 *   1. Follow queued path waypoints (A* navigation)
 *   2. Execute pending decision action (talk, interact, wait, etc.)
 *   3. Call LLM backend for next decision (cooldown ~3s)
 *   4. Idle (stand still)
 */
import Phaser from 'phaser';
import { BTState, BTNode, BTAction, BTCondition, BTSequence, BTSelector } from './BT';
import { findPath, pixelToTile, tileToPixel } from './AStar';
import { TILE } from '../config/map';

const API_BASE = 'http://localhost:8000/api/v1/dungeon';

// ── Types ──

interface LLMDecision {
  action: string;
  target_x?: number;
  target_y?: number;
  target_npc?: string;
  message?: string;
  thought?: string;
}

interface QueuedAction {
  type: 'move_to' | 'talk_to' | 'interact_with' | 'wait' | 'use';
  targetX?: number;
  targetY?: number;
  targetName?: string;
  message?: string;
}

interface MemoryEntry {
  text: string;
  importance: number; // 1-10
  timestamp: number;
  tags: string[];
}

// ── NPC species positions for navigation ──

const NPC_POSITIONS: Record<string, { x: number; y: number }> = {
  Grom: { x: 5 * TILE, y: 10 * TILE },
  Zara: { x: 15 * TILE, y: 3 * TILE },
  Finn: { x: 5 * TILE, y: 4 * TILE },
  Guard: { x: 19.5 * TILE, y: 9 * TILE },
};

const STATION_POSITIONS: Record<string, { x: number; y: number }> = {
  Anvil: { x: 3.5 * TILE, y: 14 * TILE },
  Cauldron: { x: 20 * TILE, y: 3 * TILE },
  Counter: { x: 3.5 * TILE, y: 3.5 * TILE },
};

// ── LLMNPCSprite ──

export class LLMNPCSprite extends Phaser.Physics.Arcade.Sprite {
  private tree!: BTNode;
  private label!: Phaser.GameObjects.Text;
  private speechBubble!: Phaser.GameObjects.Text;
  private memoryBubble!: Phaser.GameObjects.Text;
  private healthBar!: Phaser.GameObjects.Graphics;

  // LLM state
  private pendingDecision: LLMDecision | null = null;
  private isWaiting: boolean = false;
  private lastCallTime: number = 0;
  private readonly CALL_COOLDOWN = 8000;
  private callCount: number = 0;
  private lastStateHash: string = '';
  private idleCooldownMultiplier: number = 1;

  // Cooldown when nothing changed
  private readonly IDLE_COOLDOWN_MAX = 30000; // max 30s between calls

  // Action queue (multi-step)
  private actionQueue: QueuedAction[] = [];
  private currentQueuedAction: QueuedAction | null = null;

  // A* pathfinding
  private path: { x: number; y: number }[] = [];
  private pathIndex: number = 0;
  private readonly MOVE_SPEED = 60;
  private readonly NPC_INTERACT_DIST = 40; // pixels

  // Memory
  public memories: MemoryEntry[] = [];
  public health: number = 100;
  public inventory: string[] = ['Rusty Key'];
  public currentObjective: string = 'Find the Crystal of Eternity';
  public nearbyNPCs: { name: string; role: string; x: number; y: number }[] = [];

  // Animation
  // Callbacks
  public onMemoryUpdated: ((memories: MemoryEntry[]) => void) | null = null;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    public agentName: string = 'Kael',
    public playerRef: Phaser.GameObjects.Sprite | null = null,
    textureKey: string = 'npc',
  ) {
    super(scene, x, y, textureKey);
    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.setScale(1.3);

    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setCollideWorldBounds(true);
    body.setSize(20, 20);

    // Labels
    const labelStyle: Phaser.Types.GameObjects.Text.TextStyle = {
      fontSize: '9px',
      color: '#aaddff',
      backgroundColor: '#00000088',
      padding: { x: 2, y: 1 },
    };
    const bubbleStyle: Phaser.Types.GameObjects.Text.TextStyle = {
      fontSize: '8px',
      color: '#ffffff',
      backgroundColor: '#000000aa',
      padding: { x: 3, y: 2 },
      wordWrap: { width: 140 },
    };

    this.label = scene.add.text(x, y - 22, `${agentName}`, labelStyle)
      .setOrigin(0.5).setDepth(10);

    this.speechBubble = scene.add.text(x, y - 36, '', bubbleStyle)
      .setOrigin(0.5).setDepth(10).setAlpha(0);

    this.memoryBubble = scene.add.text(x, y - 50, '', {
      ...bubbleStyle, fontSize: '7px', color: '#88dd88',
    }).setOrigin(0.5).setDepth(10).setAlpha(0);

    // Health bar
    this.healthBar = scene.add.graphics();
    this.healthBar.setDepth(10);

    this.buildTree();
  }

  // ── BT ──

  private buildTree(): void {
    this.tree = new BTSelector([
      // Priority 1: Follow A* path
      this.makeSeq('Follow Path', [
        new BTCondition('Has path?', () => this.path.length > 0 && this.pathIndex < this.path.length),
        new BTAction('Walk path', () => this.followPath()),
      ]),
      // Priority 2: Execute action queue
      this.makeSeq('Run action queue', [
        new BTCondition('Has queued action?', () => this.actionQueue.length > 0 || this.currentQueuedAction !== null),
        new BTAction('Process queue', () => this.processActionQueue()),
      ]),
      // Priority 3: Execute pending decision (direct from LLM)
      this.makeSeq('Execute decision', [
        new BTCondition('Has decision?', () => this.pendingDecision !== null),
        new BTAction('Act', () => this.executeDecision()),
      ]),
      // Priority 4: Call LLM
      this.makeSeq('Think', [
        new BTCondition('Can think?', () => {
          if (this.isWaiting || this.pendingDecision) return false;
          const now = Date.now();
          const effectiveCooldown = this.CALL_COOLDOWN * this.idleCooldownMultiplier;
          if ((now - this.lastCallTime) <= effectiveCooldown) return false;

          // State hash — only call LLM if something actually changed
          const hash = `${Math.round(this.x)},${Math.round(this.y)}|h:${Math.round(this.health)}|inv:${this.inventory.length}|npc:${this.nearbyNPCs.map(n=>n.name).sort().join(',')}`;
          if (hash === this.lastStateHash && this.callCount > 0) {
            // Nothing changed — back off more
            this.idleCooldownMultiplier = Math.min(this.idleCooldownMultiplier * 2, this.IDLE_COOLDOWN_MAX / this.CALL_COOLDOWN);
            this.lastCallTime = now; // reset timer to use the longer cooldown
            return false;
          }
          return true;
        }),
        new BTAction('Call LLM', () => {
          this.isWaiting = true;
          this.lastCallTime = Date.now();
          this.callLLM();
          return BTState.RUNNING;
        }),
      ]),
      // Priority 5: Idle
      new BTAction('Idle', () => {
        this.setVelocity(0, 0);
        return BTState.RUNNING;
      }),
    ]);
  }

  private makeSeq(name: string, children: BTNode[]): BTNode {
    return new BTSequence(children);
  }

  // ── A* Path Following ──

  private followPath(): BTState {
    if (this.pathIndex >= this.path.length) {
      this.path = [];
      this.pathIndex = 0;
      this.setVelocity(0, 0);
      return BTState.SUCCESS;
    }

    const target = this.path[this.pathIndex];
    const targetPx = target.x * TILE + TILE / 2;
    const targetPy = target.y * TILE + TILE / 2;

    const dist = Phaser.Math.Distance.Between(this.x, this.y, targetPx, targetPy);

    if (dist < 4) {
      this.pathIndex++;
      if (this.pathIndex >= this.path.length) {
        this.path = [];
        this.pathIndex = 0;
        this.setVelocity(0, 0);
        return BTState.SUCCESS;
      }
      return BTState.RUNNING; // continue to next tile next tick
    }

    const angle = Phaser.Math.Angle.Between(this.x, this.y, targetPx, targetPy);
    this.setVelocity(Math.cos(angle) * this.MOVE_SPEED, Math.sin(angle) * this.MOVE_SPEED);
    return BTState.RUNNING;
  }

  /** Set a path to pixel coordinates using A* */
  public navigateTo(px: number, py: number): void {
    const { tx, ty } = pixelToTile(px, py);
    const { tx: stx, ty: sty } = pixelToTile(this.x, this.y);
    this.path = findPath(stx, sty, tx, ty);
    this.pathIndex = 0;

    // Debug: show path length
    this.label.setText(`${this.agentName}:${this.path.length} tiles`);
  }

  /** Is the NPC currently following a path? */
  public get isNavigating(): boolean {
    return this.path.length > 0 && this.pathIndex < this.path.length;
  }

  /** Distance to a pixel target */
  private distTo(px: number, py: number): number {
    return Phaser.Math.Distance.Between(this.x, this.y, px, py);
  }

  // ── Action Queue ──

  /**
   * Queue up a multi-step action like:
   *   talk_to(Grom) → [walk to Grom, then say message]
   */
  public queueActions(actions: QueuedAction[]): void {
    // Cancel current path if any (new action overrides)
    this.path = [];
    this.pathIndex = 0;
    this.pendingDecision = null;

    this.actionQueue.push(...actions);
    if (!this.currentQueuedAction) {
      this.currentQueuedAction = this.actionQueue.shift() ?? null;
    }
  }

  private processActionQueue(): BTState {
    if (!this.currentQueuedAction) {
      this.currentQueuedAction = this.actionQueue.shift() ?? null;
      if (!this.currentQueuedAction) return BTState.SUCCESS;
    }

    const a = this.currentQueuedAction;

    switch (a.type) {
      case 'move_to': {
        if (!a.targetX || !a.targetY) {
          this.currentQueuedAction = null;
          return BTState.SUCCESS;
        }
        if (this.distTo(a.targetX, a.targetY) < this.NPC_INTERACT_DIST) {
          this.setVelocity(0, 0);
          this.currentQueuedAction = null;
          return BTState.SUCCESS; // arrived → next in queue
        }
        // Navigate if not already
        if (!this.isNavigating) {
          this.navigateTo(a.targetX, a.targetY);
        }
        // Keep following path (handled by priority 1 in BT)
        // But we need to stay in this state until arrived
        if (this.isNavigating) {
          return BTState.RUNNING;
        }
        // Check again if arrived
        if (this.distTo(a.targetX, a.targetY) < this.NPC_INTERACT_DIST) {
          this.setVelocity(0, 0);
          this.currentQueuedAction = null;
          return BTState.SUCCESS;
        }
        // Recalculate path
        this.navigateTo(a.targetX, a.targetY);
        return BTState.RUNNING;
      }

      case 'talk_to':
        this.setVelocity(0, 0);
        if (a.message) {
          this.showSpeech(a.message);
          this.addMemory(`Talked to ${a.targetName ?? 'someone'}`, 6, ['social', 'dialogue']);
        }
        this.currentQueuedAction = null;
        return BTState.SUCCESS;

      case 'interact_with':
        this.setVelocity(0, 0);
        this.addMemory(`Interacted with ${a.targetName ?? 'object'}`, 5, ['interaction']);
        this.currentQueuedAction = null;
        return BTState.SUCCESS;

      case 'wait':
        this.setVelocity(0, 0);
        this.currentQueuedAction = null;
        return BTState.SUCCESS;

      default:
        this.currentQueuedAction = null;
        return BTState.SUCCESS;
    }
  }

  // ── LLM Decision Execution ──

  private executeDecision(): BTState {
    if (!this.pendingDecision) return BTState.FAILURE;

    const d = this.pendingDecision;
    const agentName = this.agentName;

    // Show speech
    if (d.message) {
      this.showSpeech(d.message);
    } else if (d.thought) {
      // If no message but has thought, show the thought as internal monologue
      this.showSpeech(`💭 ${d.thought}`);
    }

    // Show thought in label (truncated)
    const labelText = d.thought
      ? `${agentName}: ${d.thought.slice(0, 25)}${d.thought.length > 25 ? '…' : ''}`
      : `${agentName}:${d.action}`;
    this.label.setText(labelText);

    switch (d.action) {
      case 'move':
      case 'explore': {
        const tx = d.target_x ?? this.x + 50;
        const ty = d.target_y ?? this.y;
        this.navigateTo(tx, ty);
        this.pendingDecision = null;
        return BTState.SUCCESS;
      }

      case 'talk': {
        const npcName = d.target_npc;
        const npcPos = npcName ? NPC_POSITIONS[npcName] : null;

        if (npcPos) {
          // Walk to NPC first, then talk
          this.queueActions([
            { type: 'move_to', targetX: npcPos.x, targetY: npcPos.y, targetName: npcName },
            { type: 'talk_to', targetName: npcName, message: d.message },
          ]);
        } else {
          // No known NPC — just say the line
          this.showSpeech(d.message ?? 'Hello?');
        }

        if (d.thought) {
          this.addMemory(d.thought, 7, ['dialogue', 'social']);
        }
        this.pendingDecision = null;
        return BTState.SUCCESS;
      }

      case 'interact': {
        // Find nearest object
        const objP = this.findNearestObject();
        if (objP) {
          this.queueActions([
            { type: 'move_to', targetX: objP.x, targetY: objP.y, targetName: objP.name },
            { type: 'interact_with', targetName: objP.name, message: d.message },
          ]);
        } else {
          this.showSpeech('Nothing to interact with.');
        }
        this.addMemory(d.thought ?? `Interacting with something.`, 5, ['interaction']);
        this.pendingDecision = null;
        return BTState.SUCCESS;
      }

      case 'wait':
        this.setVelocity(0, 0);
        this.addMemory(d.thought ?? `Waiting and observing.`, 3, ['observation']);
        this.pendingDecision = null;
        return BTState.SUCCESS;

      case 'use': {
        const item = this.inventory[0];
        this.addMemory(`Used ${item ?? 'item'}`, 4, ['inventory']);
        this.showSpeech(`Using ${item ?? 'item'}...`);
        this.pendingDecision = null;
        return BTState.SUCCESS;
      }

      default:
        this.pendingDecision = null;
        this.setVelocity(0, 0);
        return BTState.SUCCESS;
    }
  }

  private findNearestObject(): { x: number; y: number; name: string } | null {
    let nearest: { x: number; y: number; name: string; dist: number } | null = null;
    for (const [name, pos] of Object.entries(STATION_POSITIONS)) {
      const d = this.distTo(pos.x, pos.y);
      if (!nearest || d < nearest.dist) {
        nearest = { ...pos, name, dist: d };
      }
    }
    return nearest ? { x: nearest.x, y: nearest.y, name: nearest.name } : null;
  }

  // ── LLM API ──

  private async callLLM(): Promise<void> {
    this.label.setText(`${this.agentName}: thinking...`);

    this.callCount++;
    this.lastCallTime = Date.now();

    // Update state hash after successful call
    this.idleCooldownMultiplier = 1;

    try {
      const recentMemories = this.memories.slice(-5).map(m => m.text);
      const nearbyNPCs = this.nearbyNPCs.map(n => ({
        name: n.name, role: n.role, x: n.x, y: n.y,
      }));

      const body = JSON.stringify({
        agent_name: this.agentName,
        agent_x: this.x,
        agent_y: this.y,
        health: this.health,
        inventory: this.inventory,
        nearby_npcs: nearbyNPCs,
        nearby_objects: Object.entries(STATION_POSITIONS).map(([name, pos]) => ({
          name, x: pos.x, y: pos.y,
        })),
        recent_memories: recentMemories,
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

      // Store memory from LLM thought
      if (decision.thought) {
        this.addMemory(decision.thought, 7, ['llm', 'reasoning']);
      }

      // Show speech — show thought alongside message for richer display
      const bubbleContent = decision.message
        ? (decision.thought ? `${decision.message} 💭 ${decision.thought}` : decision.message)
        : (decision.thought ? `💭 ${decision.thought}` : '');
      if (bubbleContent && !['talk', 'interact'].includes(decision.action)) {
        // For talk/interact, speech is shown during execution when we arrive
        this.showSpeech(bubbleContent);
      }

    } catch (err) {
      console.warn('[LLM NPC] API call failed:', err);
      this.pendingDecision = {
        action: 'move',
        target_x: this.x + (Math.random() - 0.5) * 100,
        target_y: this.y + (Math.random() - 0.5) * 100,
        message: 'Hmm, something disrupted my connection.',
        thought: 'Lost connection to my reasoning center. Exploring randomly.',
      };
    }

    this.isWaiting = false;
  }

  // ── Memory System ──

  /** Add a memory with importance scoring */
  public addMemory(text: string, importance: number = 5, tags: string[] = []): void {
    this.memories.push({
      text,
      importance: Math.max(1, Math.min(10, importance)),
      timestamp: Date.now(),
      tags,
    });

    // Decay old memories: reduce importance of older entries
    this.decayMemories();

    // Prune if too many
    if (this.memories.length > 30) {
      // Keep top 20 by (importance + recency)
      const now = Date.now();
      this.memories.sort((a, b) => {
        const scoreA = a.importance * (1 + 0.1 * Math.max(0, 1 - (now - a.timestamp) / 120000));
        const scoreB = b.importance * (1 + 0.1 * Math.max(0, 1 - (now - b.timestamp) / 120000));
        return scoreB - scoreA;
      });
      this.memories = this.memories.slice(0, 20);
    }

    // Update memory bubble briefly
    this.memoryBubble.setText(`🧠 ${this.memories.length} mems`);
    this.memoryBubble.setAlpha(1);
    this.scene.time.delayedCall(2000, () => {
      this.memoryBubble.setAlpha(0.4);
    });

    // Notify listener
    this.onMemoryUpdated?.(this.memories);
  }

  /** Decay: older memories lose importance */
  private decayMemories(): void {
    const now = Date.now();
    for (const m of this.memories) {
      const age = (now - m.timestamp) / 1000; // seconds
      if (age > 60) {
        // Lose 0.5 importance per minute, min 1
        m.importance = Math.max(1, m.importance - 0.5 * (age / 60));
      }
    }
  }

  /** Get memories relevant to a keyword */
  public getRelevantMemories(keyword: string, maxResults: number = 3): MemoryEntry[] {
    const lower = keyword.toLowerCase();
    const scored = this.memories
      .map(m => ({
        mem: m,
        relevance: m.text.toLowerCase().includes(lower) ? m.importance * 2 : 0,
      }))
      .filter(s => s.relevance > 0)
      .sort((a, b) => b.relevance - a.relevance);
    return scored.slice(0, maxResults).map(s => s.mem);
  }

  /** Summarize memories for LLM context */
  public get memorySummary(): string {
    if (this.memories.length === 0) return 'No memories yet.';
    const recent = this.memories.slice(-5);
    return recent.map(m => `[${m.importance.toFixed(0)}] ${m.text}`).join('\n');
  }

  // ── Visual Feedback ──

  public showSpeech(text: string): void {
    const displayText = text.length > 120 ? text.slice(0, 117) + '...' : text;
    this.speechBubble.setText(`"${displayText}"`);
    this.speechBubble.setAlpha(1);
    // Duration proportional to text length: min 3s, ~100ms per char, max 12s
    const duration = Math.max(3000, Math.min(12000, text.length * 100));
    // Clear any existing timer to avoid overlap
    if ((this as any).__speechTimer) {
      this.scene.time.removeEvent((this as any).__speechTimer);
    }
    (this as any).__speechTimer = this.scene.time.delayedCall(duration, () => {
      this.speechBubble.setAlpha(0);
      (this as any).__speechTimer = null;
    });
    // Sparkle burst — create temporary bright sprites
    // Audio sparkle
    const gs = this.scene as any;
    if (gs.audio) gs.audio.playSparkle();
    for (let i = 0; i < 8; i++) {
      const angle = (Math.PI * 2 / 8) * i + Math.random() * 0.5;
      const dist = 10 + Math.random() * 20;
      const sx = this.x + Math.cos(angle) * dist;
      const sy = (this.y - 10) + Math.sin(angle) * dist;
      const star = this.scene.add.circle(sx, sy, 2 + Math.random() * 1, 0xffffaa, 1);
      star.setDepth(50);
      this.scene.tweens.add({
        targets: star,
        alpha: 0,
        scale: 1.5,
        duration: 300 + Math.random() * 200,
        ease: 'Quad.easeOut',
        onComplete: () => star.destroy(),
      });
    }
  }

  // ── Update ──

  update(_delta: number): void {
    this.tree.tick();

    // Position labels
    this.label.setPosition(this.x, this.y - 22);
    this.speechBubble.setPosition(this.x, this.y - 38);
    this.memoryBubble.setPosition(this.x, this.y - 52);
    this.setDepth(this.y);
    this.label.setDepth(this.y + 1);
    this.speechBubble.setDepth(this.y + 1);
    this.memoryBubble.setDepth(this.y + 1);

    // Health bar
    this.drawHealthBar();

    // Walk animation placeholder
  }

  private drawHealthBar(): void {
    this.healthBar.clear();
    this.healthBar.setPosition(this.x - 12, this.y - 30);

    // Background (dark red)
    this.healthBar.fillStyle(0x441111, 1);
    this.healthBar.fillRect(0, 0, 24, 3);

    // Health fill (green → yellow → red)
    const ratio = Math.max(0, this.health / 100);
    const hColor = ratio > 0.6 ? 0x44cc44 : ratio > 0.3 ? 0xcccc44 : 0xcc4444;
    this.healthBar.fillStyle(hColor, 1);
    this.healthBar.fillRect(0, 0, 24 * ratio, 3);

    // Border
    this.healthBar.lineStyle(1, 0xffffff, 0.3);
    this.healthBar.strokeRect(0, 0, 24, 3);
  }

  destroy() {
    this.label?.destroy();
    this.speechBubble?.destroy();
    this.memoryBubble?.destroy();
    super.destroy();
  }
}
