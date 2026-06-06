import Phaser from 'phaser';

/**
 * BootScene — generates all procedural textures so we don't need image files.
 * Phase 0, Quest 0.2: Load assets, render a sprite.
 */
export class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: 'BootScene' });
  }

  create(): void {
    this.generateTextures();
    this.scene.start('GameScene');
  }

  private generateTextures(): void {
    // --- Player (blue circle with outline) ---
    // Helper: create a temp graphics, generate a texture, then destroy
    const makeTex = (key: string, w: number, h: number, draw: (g: Phaser.GameObjects.Graphics) => void) => {
      const g = this.add.graphics();
      draw(g);
      g.generateTexture(key, w, h);
      g.destroy();
    };

    // Player (blue circle with outline)
    makeTex('player', 32, 32, (g) => {
      g.fillStyle(0x4488ff, 1);
      g.fillCircle(16, 16, 14);
      g.lineStyle(2, 0xffffff, 0.8);
      g.strokeCircle(16, 16, 14);
    });

    // Floor tile (dark stone)
    makeTex('floor', 32, 32, (g) => {
      g.fillStyle(0x2a2a3a, 1);
      g.fillRect(0, 0, 32, 32);
      g.lineStyle(1, 0x3a3a4a, 0.5);
      g.strokeRect(0, 0, 32, 32);
    });

    // Wall tile (gray brick)
    makeTex('wall', 32, 32, (g) => {
      g.fillStyle(0x555577, 1);
      g.fillRect(0, 0, 32, 32);
      g.lineStyle(2, 0x333355, 1);
      g.strokeRect(0, 0, 32, 32);
      g.lineStyle(1, 0x444466, 0.6);
      g.lineBetween(0, 16, 32, 16);
      g.lineBetween(16, 0, 16, 16);
      g.lineBetween(0, 16, 0, 32);
    });

    // Door tile (brown)
    makeTex('door', 32, 32, (g) => {
      g.fillStyle(0x8b4513, 1);
      g.fillRect(0, 0, 32, 32);
      g.lineStyle(2, 0xa0522d, 1);
      g.strokeRect(2, 2, 28, 28);
    });

    // NPC dot (green)
    makeTex('npc', 24, 24, (g) => {
      g.fillStyle(0x44cc44, 1);
      g.fillCircle(12, 12, 10);
      g.lineStyle(1, 0x88ff88, 0.8);
      g.strokeCircle(12, 12, 10);
    });
  }
}
