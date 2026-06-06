import Phaser from 'phaser';
import { NPCBrain } from './NPCBrain';

export type NPCRole = 'blacksmith' | 'alchemist' | 'merchant';

interface WorkStation {
  x: number;
  y: number;
  name: string;
}

export class NPCSprite extends Phaser.Physics.Arcade.Sprite {
  public brain: NPCBrain;
  public role: NPCRole;

  private boredom: number = 0;
  private workTimer: number = 0;
  private homeX: number;
  private homeY: number;
  private moveTarget: Phaser.Math.Vector2 | null = null;
  private maxWanderDist: number = 80;

  // Visual indicators
  private stateLabel!: Phaser.GameObjects.Text;
  private roleLabel!: Phaser.GameObjects.Text;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    name: string,
    role: NPCRole,
    public workstation: WorkStation | null = null,
    textureKey: string = 'npc',
  ) {
    super(scene, x, y, textureKey);
    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.homeX = x;
    this.homeY = y;
    this.role = role;

    // Physics body
    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setCollideWorldBounds(true);
    body.setSize(20, 20);

    // Name label
    this.stateLabel = scene.add.text(x, y - 18, 'idle', {
      fontSize: '9px',
      color: '#ffffff',
      backgroundColor: '#00000088',
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5).setDepth(10);

    // Role label
    this.roleLabel = scene.add.text(x, y + 14, role, {
      fontSize: '8px',
      color: '#cccccc',
      backgroundColor: '#00000088',
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5).setDepth(10);

    // Create FSM brain
    this.brain = new NPCBrain({
      name,
      idle: () => this.beIdle(),
      wander: () => this.beWander(),
      work: () => this.beWork(),
      getBoredom: () => this.boredom,
      hasWork: () => this.workstation !== null,
    });
  }

  /** Called from Phaser update() */
  update(delta: number): void {
    // Tick the FSM brain
    this.brain.update();

    // Move toward target if set
    if (this.moveTarget) {
      const dist = Phaser.Math.Distance.Between(this.x, this.y, this.moveTarget.x, this.moveTarget.y);
      if (dist < 8) {
        // Arrived
        this.setVelocity(0, 0);
        this.moveTarget = null;
      } else {
        const speed = this.brain.currentState === 'work' ? 80 : 40;
        const angle = Phaser.Math.Angle.Between(this.x, this.y, this.moveTarget.x, this.moveTarget.y);
        this.setVelocity(Math.cos(angle) * speed, Math.sin(angle) * speed);
      }
    } else {
      this.setVelocity(0, 0);
    }

    // Update floating labels
    this.stateLabel.setPosition(this.x, this.y - 18);
    this.stateLabel.setText(this.brain.currentState);

    this.roleLabel.setPosition(this.x, this.y + 14);

    // Depth sorting (higher Y = higher depth)
    this.setDepth(this.y);
    this.stateLabel.setDepth(this.y + 1);
    this.roleLabel.setDepth(this.y + 1);
  }

  private beIdle(): void {
    this.boredom += 0.1;
    this.moveTarget = null;
    this.setVelocity(0, 0);
  }

  private beWander(): void {
    this.boredom -= 0.2;
    if (!this.moveTarget) {
      // Pick random point near home
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * this.maxWanderDist;
      this.moveTarget = new Phaser.Math.Vector2(
        this.homeX + Math.cos(angle) * dist,
        this.homeY + Math.sin(angle) * dist
      );
    }
  }

  private beWork(): void {
    this.boredom = 0;
    if (!this.workstation) return;

    if (!this.moveTarget) {
      // Move toward workstation
      this.moveTarget = new Phaser.Math.Vector2(this.workstation.x, this.workstation.y);
    } else {
      // At workstation — simulate work
      this.setVelocity(0, 0);
      this.workTimer += 0.016; // ~1 frame
    }
  }

  /** Clean up when destroying */
  destroy() {
    this.stateLabel?.destroy();
    this.roleLabel?.destroy();
    super.destroy();
  }
}
