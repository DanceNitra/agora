/**
 * VerminSprite — roaming dungeon vermin (rats, slimes, etc.)
 * 
 * Behavior:
 *  - Random wander within a home zone
 *  - Flee from player if too close
 *  - Can be damaged by spacebar attack
 *  - Dies after taking enough damage
 */
import Phaser from 'phaser';

const VERMIN_COLORS = [0x886644, 0x668844, 0x884466, 0x446688];

export class VerminSprite extends Phaser.Physics.Arcade.Sprite {
  private homeX: number;
  private homeY: number;
  private wanderTarget: Phaser.Math.Vector2 | null = null;
  private wanderTimer: number = 0;
  private readonly WANDER_RADIUS = 60;
  private readonly FLEE_DIST = 80;
  private readonly MOVE_SPEED = 30 + Math.random() * 20;

  public hp: number = 3;
  private maxHp: number = 3;
  private damageFlashTimer: number = 0;
  private isDead: boolean = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    public playerRef: Phaser.GameObjects.Sprite | null = null,
    public verminType: 'rat' | 'slime' | 'spider' = 'rat',
  ) {
    super(scene, x, y, 'vermin');
    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.homeX = x;
    this.homeY = y;

    const tintColor = VERMIN_COLORS[Math.floor(Math.random() * VERMIN_COLORS.length)];
    this.setTint(tintColor);
    this.setScale(0.8 + Math.random() * 0.4);

    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setCollideWorldBounds(true);
    body.setSize(12, 10);
    body.setOffset(4, 6);
  }

  update(_delta: number): void {
    if (this.isDead) return;

    // Damage flash
    if (this.damageFlashTimer > 0) {
      this.damageFlashTimer -= 16;
      this.setAlpha(this.damageFlashTimer % 100 < 50 ? 0.3 : 1);
    } else {
      this.setAlpha(1);
      this.setTint(VERMIN_COLORS[Math.floor(Math.random() * VERMIN_COLORS.length)]); // subtle random tint variation
    }

    const player = this.playerRef;
    const distToPlayer = player
      ? Phaser.Math.Distance.Between(this.x, this.y, player.x, player.y)
      : 999;

    // Flee from player if too close
    if (distToPlayer < this.FLEE_DIST && player) {
      const angle = Phaser.Math.Angle.Between(player.x, player.y, this.x, this.y);
      this.setVelocity(
        Math.cos(angle) * this.MOVE_SPEED * 1.5,
        Math.sin(angle) * this.MOVE_SPEED * 1.5,
      );
      this.setFlipX(angle < 0);
      this.setDepth(this.y);
      return;
    }

    // Wander
    this.wanderTimer += 16;
    if (!this.wanderTarget || this.wanderTimer > 2000) {
      this.wanderTimer = 0;
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * this.WANDER_RADIUS;
      this.wanderTarget = new Phaser.Math.Vector2(
        this.homeX + Math.cos(angle) * dist,
        this.homeY + Math.sin(angle) * dist,
      );
    }

    if (this.wanderTarget) {
      const d = Phaser.Math.Distance.Between(this.x, this.y, this.wanderTarget.x, this.wanderTarget.y);
      if (d < 8) {
        this.setVelocity(0, 0);
        this.wanderTarget = null;
      } else {
        const angle = Phaser.Math.Angle.Between(this.x, this.y, this.wanderTarget.x, this.wanderTarget.y);
        this.setVelocity(Math.cos(angle) * this.MOVE_SPEED, Math.sin(angle) * this.MOVE_SPEED);
        this.setFlipX(angle < 0);
      }
    } else {
      this.setVelocity(0, 0);
    }

    this.setDepth(this.y);
  }

  /** Called when player attacks this vermin. Returns true if killed. */
  public takeDamage(amount: number = 1): boolean {
    if (this.isDead) return false;
    this.hp -= amount;
    this.damageFlashTimer = 200;

    if (this.hp <= 0) {
      this.die();
      return true;
    }
    return false;
  }

  private die(): void {
    this.isDead = true;
    this.setVelocity(0, 0);
    this.setAlpha(0);
    this.body?.enable && ((this.body as Phaser.Physics.Arcade.Body).enable = false);

    // Sink into floor animation
    this.scene.tweens.add({
      targets: this,
      alpha: 0,
      scale: 0,
      duration: 300,
      onComplete: () => this.destroy(),
    });
  }

  public get alive(): boolean {
    return !this.isDead;
  }

  destroy() {
    super.destroy();
  }
}
