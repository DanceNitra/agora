import Phaser from 'phaser';
import {
  BTState, BTNode,
  BTAction, BTCondition,
  BTSequence, BTSelector,
} from './BT';

/**
 * BTNPCSprite — NPC driven by a Behavior Tree instead of FSM.
 * Demonstrates Selector(fallback) + Sequence priorities.
 * Patrol → Follow Player if close → Flee if too far from home.
 */
export class BTNPCSprite extends Phaser.Physics.Arcade.Sprite {
  private tree!: BTNode;
  private homeX: number;
  private homeY: number;
  private moveTarget: Phaser.Math.Vector2 | null = null;
  private label!: Phaser.GameObjects.Text;

  public isPatrolling: boolean = false;
  public isFollowing: boolean = false;
  public isReturning: boolean = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    name: string,
    public followTarget: Phaser.GameObjects.Sprite | null = null
  ) {
    super(scene, x, y, 'npc');
    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.homeX = x;
    this.homeY = y;

    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setCollideWorldBounds(true);
    body.setSize(20, 20);

    // Label
    this.label = scene.add.text(x, y - 18, name, {
      fontSize: '9px',
      color: '#ffcc00',
      backgroundColor: '#00000088',
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5).setDepth(10);

    // Build the Behavior Tree
    this.buildTree();
  }

  private buildTree(): void {
    this.tree = new BTSelector([
      // Priority 1: If too far from home → return
      this.makeSequence("Return home", [
        new BTCondition("Too far?", () => {
          const d = Phaser.Math.Distance.Between(this.x, this.y, this.homeX, this.homeY);
          return d > 150;
        }),
        new BTAction("Walk home", () => {
          this.isReturning = true;
          this.isPatrolling = false;
          this.isFollowing = false;
          return this.moveToward(this.homeX, this.homeY, 60);
        }),
      ]),

      // Priority 2: If player is close → follow them
      this.makeSequence("Follow player", [
        new BTCondition("Player close?", () => {
          if (!this.followTarget) return false;
          return Phaser.Math.Distance.Between(this.x, this.y, this.followTarget.x, this.followTarget.y) < 120;
        }),
        new BTAction("Follow player", () => {
          this.isFollowing = true;
          this.isPatrolling = false;
          this.isReturning = false;
          if (!this.followTarget) return BTState.FAILURE;
          return this.moveToward(this.followTarget.x, this.followTarget.y, 80);
        }),
      ]),

      // Priority 3: Default patrol
      this.makeSequence("Patrol", [
        new BTAction("Patrol area", () => {
          this.isPatrolling = true;
          this.isFollowing = false;
          this.isReturning = false;

          if (!this.moveTarget || this.reachedTarget()) {
            // Pick a random patrol point near home
            const angle = Math.random() * Math.PI * 2;
            const dist = 40 + Math.random() * 80;
            this.moveTarget = new Phaser.Math.Vector2(
              this.homeX + Math.cos(angle) * dist,
              this.homeY + Math.sin(angle) * dist
            );
          }
          return this.moveToward(this.moveTarget.x, this.moveTarget.y, 40);
        }),
      ]),
    ]);
  }

  private makeSequence(name: string, children: BTNode[]): BTNode {
    return new BTSequence(children);
  }

  /** Move toward (x,y) at given speed. Returns RUNNING while en route, SUCCESS when arrived. */
  private moveToward(tx: number, ty: number, speed: number): BTState {
    const dist = Phaser.Math.Distance.Between(this.x, this.y, tx, ty);
    if (dist < 8) {
      this.setVelocity(0, 0);
      return BTState.SUCCESS;
    }
    const angle = Phaser.Math.Angle.Between(this.x, this.y, tx, ty);
    this.setVelocity(Math.cos(angle) * speed, Math.sin(angle) * speed);
    return BTState.RUNNING;
  }

  private reachedTarget(): boolean {
    if (!this.moveTarget) return true;
    return Phaser.Math.Distance.Between(this.x, this.y, this.moveTarget.x, this.moveTarget.y) < 12;
  }

  /** Call from Phaser update() */
  update(): void {
    // Tick the behavior tree
    const status = this.tree.tick();

    // Update label
    let action = 'patrol';
    if (this.isFollowing) action = 'follow';
    if (this.isReturning) action = 'return';
    if (status === BTState.SUCCESS) action = 'idle';

    this.label.setPosition(this.x, this.y - 18);
    this.label.setText(`Guard:${action}`);
    this.setDepth(this.y);
    this.label.setDepth(this.y + 1);
  }

  destroy() {
    this.label?.destroy();
    super.destroy();
  }
}
