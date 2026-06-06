import { TILE, MAP_W, MAP_H, DUNGEON_MAP } from './config/map';

export class MinimapOverlay {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private readonly mmW = 120;
  private readonly mmH = 100;

  constructor() {
    this.canvas = document.createElement('canvas');
    this.canvas.width = this.mmW;
    this.canvas.height = this.mmH;
    this.canvas.style.cssText = `
      position: fixed;
      bottom: 8px;
      right: 8px;
      width: 120px;
      height: 100px;
      border-radius: 4px;
      border: 1px solid #444466;
      z-index: 9999;
      pointer-events: none;
      opacity: 0.7;
    `;
    document.body.appendChild(this.canvas);
    const ctx = this.canvas.getContext('2d');
    if (!ctx) throw new Error('Failed to get 2D context');
    this.ctx = ctx;
  }

  update(
    playerX: number,
    playerY: number,
    npcPositions: { x: number; y: number }[]
  ): void {
    const ctx = this.ctx;
    const { mmW, mmH } = this;
    const scaleX = mmW / (MAP_W * TILE);
    const scaleY = mmH / (MAP_H * TILE);

    // Clear
    ctx.clearRect(0, 0, mmW, mmH);

    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(0, 0, mmW, mmH);

    // Walls
    ctx.fillStyle = 'rgba(68, 68, 85, 0.8)';
    for (let y = 0; y < MAP_H; y++) {
      for (let x = 0; x < MAP_W; x++) {
        if (DUNGEON_MAP[y]?.[x] === 1) {
          ctx.fillRect(
            x * TILE * scaleX,
            y * TILE * scaleY,
            Math.max(1, TILE * scaleX),
            Math.max(1, TILE * scaleY),
          );
        }
      }
    }

    // NPCs (green dots)
    ctx.fillStyle = '#44ff88';
    for (const npc of npcPositions) {
      ctx.beginPath();
      ctx.arc(npc.x * scaleX, npc.y * scaleY, 2, 0, Math.PI * 2);
      ctx.fill();
    }

    // Player (blue dot)
    ctx.fillStyle = '#4488ff';
    ctx.beginPath();
    ctx.arc(playerX * scaleX, playerY * scaleY, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#88bbff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(playerX * scaleX, playerY * scaleY, 3, 0, Math.PI * 2);
    ctx.stroke();
  }

  destroy(): void {
    this.canvas.remove();
  }
}
