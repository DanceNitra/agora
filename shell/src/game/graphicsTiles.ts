/**
 * graphicsTiles.ts — PixiJS-native tile generation using Graphics API.
 *
 * Instead of Canvas2D pixel textures, this uses PixiJS Graphics (vector)
 * rendered to RenderTextures for clean, scalable, high-quality tiles.
 *
 * Run AFTER the PixiJS Application is created (needs renderer).
 */

import { Graphics, RenderTexture, Texture, Application, Container } from 'pixi.js';

// ── Floor tile ──
export function createFloorTexture(app: Application): Texture {
  const g = new Graphics();

  // Base
  g.rect(0, 0, 32, 32);
  g.fill({ color: 0x2a2a38 });

  // Inner highlight (top-left light source)
  g.rect(1, 1, 30, 30);
  g.fill({ color: 0x32324a });

  // Subtle gradient overlay — darker toward bottom-right
  for (let i = 0; i < 16; i++) {
    const alpha = 0.008 * (16 - i);
    g.rect(16 + i, i, 16 - i, 32 - i * 2);
    g.fill({ color: 0x000000, alpha });
  }

  // Stone edge lines (diagonal grain)
  g.moveTo(0, 10);
  g.lineTo(32, 10);
  g.moveTo(0, 21);
  g.lineTo(32, 21);
  g.stroke({ color: 0x1a1a28, alpha: 0.3, width: 1 });

  // Tiny specks for stone texture
  for (let i = 0; i < 8; i++) {
    const sx = 4 + Math.random() * 24;
    const sy = 4 + Math.random() * 24;
    g.circle(sx, sy, 0.5 + Math.random());
    g.fill({ color: Math.random() > 0.5 ? 0x3a3a55 : 0x1a1a28, alpha: 0.3 });
  }

  // Top-left edge highlight
  g.moveTo(0, 0);
  g.lineTo(32, 0);
  g.stroke({ color: 0x444460, alpha: 0.2, width: 1 });
  g.moveTo(0, 0);
  g.lineTo(0, 32);
  g.stroke({ color: 0x444460, alpha: 0.2, width: 1 });

  // Bottom-right edge shadow
  g.moveTo(0, 31);
  g.lineTo(32, 31);
  g.stroke({ color: 0x000000, alpha: 0.15, width: 1 });
  g.moveTo(31, 0);
  g.lineTo(31, 32);
  g.stroke({ color: 0x000000, alpha: 0.15, width: 1 });

  return renderToTexture(app, g, 'floor');
}

// ── Wall tile ──
export function createWallTexture(app: Application): Texture {
  const g = new Graphics();

  // Dark base
  g.rect(0, 0, 32, 32);
  g.fill({ color: 0x2a2a40 });

  // Brick color variation rows
  const bricks = [
    { x: 0, y: 0, w: 15, h: 8, color: 0x3a3a58 },
    { x: 17, y: 0, w: 15, h: 8, color: 0x404060 },
    { x: 8, y: 9, w: 15, h: 8, color: 0x383850 },
    { x: 0, y: 18, w: 15, h: 7, color: 0x3c3c5a },
    { x: 17, y: 18, w: 15, h: 7, color: 0x424264 },
    { x: 8, y: 26, w: 15, h: 6, color: 0x36364e },
  ];

  for (const b of bricks) {
    // Brick body with rounded corners
    g.roundRect(b.x + 1, b.y + 1, b.w - 2, b.h - 2, 1);
    g.fill({ color: b.color });

    // Top highlight
    g.rect(b.x + 2, b.y + 1, b.w - 4, 1);
    g.fill({ color: 0xffffff, alpha: 0.08 });

    // Left highlight
    g.rect(b.x + 1, b.y + 2, 1, b.h - 4);
    g.fill({ color: 0xffffff, alpha: 0.05 });

    // Bottom shadow
    g.rect(b.x + 2, b.y + b.h - 2, b.w - 4, 1);
    g.fill({ color: 0x000000, alpha: 0.12 });

    // Right shadow
    g.rect(b.x + b.w - 2, b.y + 2, 1, b.h - 4);
    g.fill({ color: 0x000000, alpha: 0.08 });
  }

  // Mortar lines
  g.moveTo(0, 8); g.lineTo(32, 8);
  g.moveTo(0, 17); g.lineTo(32, 17);
  g.moveTo(0, 25); g.lineTo(32, 25);
  g.moveTo(15, 0); g.lineTo(15, 8);
  g.moveTo(7, 9); g.lineTo(7, 17);
  g.moveTo(23, 9); g.lineTo(23, 17);
  g.moveTo(15, 18); g.lineTo(15, 25);
  g.moveTo(7, 26); g.lineTo(7, 32);
  g.moveTo(23, 26); g.lineTo(23, 32);
  g.stroke({ color: 0x1a1a30, alpha: 0.8, width: 1 });

  // Top light sweep
  g.rect(0, 0, 32, 3);
  g.fill({ color: 0xffffff, alpha: 0.04 });

  // Bottom shadow
  g.rect(0, 29, 32, 3);
  g.fill({ color: 0x000000, alpha: 0.08 });

  return renderToTexture(app, g, 'wall');
}

// ── Door tile ──
export function createDoorTexture(app: Application): Texture {
  const g = new Graphics();

  // Door frame
  g.rect(0, 0, 32, 32);
  g.fill({ color: 0x1a1008 });

  // Left panel
  g.rect(2, 1, 13, 30);
  g.fill({ color: 0x5a3a22 });

  // Right panel
  g.rect(17, 1, 13, 30);
  g.fill({ color: 0x4a2a1a });

  // Plank vertical lines
  g.moveTo(15, 0); g.lineTo(15, 32);
  g.stroke({ color: 0x1a0a00, alpha: 0.6, width: 1 });

  // Iron bands
  g.rect(0, 5, 32, 3);
  g.fill({ color: 0x444466 });
  g.rect(0, 24, 32, 3);
  g.fill({ color: 0x444466 });

  // Rivets
  for (const rx of [5, 16, 27]) {
    for (const ry of [6, 25]) {
      g.circle(rx, ry, 1.5);
      g.fill({ color: 0x8888aa });
    }
  }

  // Handle
  g.circle(25, 16, 2.5);
  g.fill({ color: 0xcccc88 });
  g.circle(25, 16, 2.5);
  g.stroke({ color: 0xaaaa66, width: 1 });

  // Top highlight
  g.rect(0, 0, 32, 1);
  g.fill({ color: 0xffffff, alpha: 0.06 });

  return renderToTexture(app, g, 'door');
}

// ── Pillar ──
export function createPillarTexture(app: Application): Texture {
  const g = new Graphics();

  // Pillar shaft
  g.rect(4, 4, 12, 24);
  g.fill({ color: 0x4a4a66 });

  // Shading — left light, right dark
  g.rect(4, 4, 4, 24);
  g.fill({ color: 0x5a5a76 });
  g.rect(12, 4, 4, 24);
  g.fill({ color: 0x3a3a52 });

  // Base
  g.rect(2, 26, 16, 6);
  g.fill({ color: 0x3a3a52 });
  g.rect(2, 26, 16, 2);
  g.fill({ color: 0x5a5a76 });

  // Capital (top)
  g.rect(2, 0, 16, 5);
  g.fill({ color: 0x3a3a52 });
  g.rect(2, 0, 16, 2);
  g.fill({ color: 0x5a5a76 });

  // Grooves
  g.moveTo(6, 6); g.lineTo(6, 26);
  g.moveTo(14, 6); g.lineTo(14, 26);
  g.stroke({ color: 0x2a2a40, alpha: 0.5, width: 1 });

  return renderToTexture(app, g, 'pillar');
}

// ── Chest ──
export function createChestTexture(app: Application): Texture {
  const g = new Graphics();

  // Body
  g.roundRect(2, 8, 20, 12, 2);
  g.fill({ color: 0x7a4a2a });

  // Lid
  g.roundRect(1, 3, 22, 6, 2);
  g.fill({ color: 0x8b5e3c });

  // Lid highlight
  g.rect(2, 4, 20, 1);
  g.fill({ color: 0xaa7a55 });

  // Lock
  g.circle(12, 12, 3);
  g.fill({ color: 0xffcc44 });
  g.rect(11, 10, 2, 4);
  g.fill({ color: 0xccaa33 });

  // Iron bands
  g.rect(3, 8, 2, 12);
  g.fill({ color: 0x888899 });
  g.rect(19, 8, 2, 12);
  g.fill({ color: 0x888899 });

  return renderToTexture(app, g, 'chest');
}

// ── Torch ──
export function createTorchTexture(app: Application): Texture {
  const g = new Graphics();

  // Bracket
  g.rect(5, 12, 6, 12);
  g.fill({ color: 0x444455 });

  // Flame outer
  g.circle(8, 5, 6);
  g.fill({ color: 0xff6600 });

  // Flame mid
  g.circle(8, 4, 4);
  g.fill({ color: 0xffaa00 });

  // Flame core
  g.circle(8, 3, 2);
  g.fill({ color: 0xffeecc });

  return renderToTexture(app, g, 'torch');
}

// ── Agent sprite ──
export function createAgentTexture(app: Application, color: number, key: string): Texture {
  const g = new Graphics();

  // Body circle (cloak)
  g.circle(10, 12, 8);
  g.fill({ color });

  // Inner highlight
  g.circle(10, 10, 5);
  g.fill({ color: lightenColor(color, 30) });

  // Head
  g.circle(10, 4, 4);
  g.fill({ color: 0xddbb99 });

  // Hood (darker than body)
  g.circle(10, 3, 4);
  g.fill({ color: darkenColor(color, 20), alpha: 0.6 });

  // Eyes
  g.circle(8, 3, 0.8);
  g.fill({ color: 0xffffff });
  g.circle(12, 3, 0.8);
  g.fill({ color: 0xffffff });

  // Glow effect under agent
  g.circle(10, 18, 6);
  g.fill({ color, alpha: 0.15 });

  return renderToTexture(app, g, key);
}

// ── Helpers ──
function renderToTexture(app: Application, g: Graphics, key: string): Texture {
  const rt = RenderTexture.create({ width: 32, height: 32 });
  app.renderer.render({ container: g, target: rt });
  g.destroy();
  return rt;
}

function lightenColor(color: number, amount: number): number {
  let r = ((color >> 16) & 0xff) + amount;
  let g2 = ((color >> 8) & 0xff) + amount;
  let b = (color & 0xff) + amount;
  r = Math.min(255, r);
  g2 = Math.min(255, g2);
  b = Math.min(255, b);
  return (r << 16) | (g2 << 8) | b;
}

function darkenColor(color: number, amount: number): number {
  let r = Math.max(0, ((color >> 16) & 0xff) - amount);
  let g2 = Math.max(0, ((color >> 8) & 0xff) - amount);
  let b = Math.max(0, (color & 0xff) - amount);
  return (r << 16) | (g2 << 8) | b;
}

// ── Generate all textures (called after app.init) ──
export function generatePixiTextures(app: Application): Record<string, Texture> {
  return {
    floor: createFloorTexture(app),
    wall: createWallTexture(app),
    door: createDoorTexture(app),
    pillar: createPillarTexture(app),
    chest: createChestTexture(app),
    torch: createTorchTexture(app),
    // Agent textures with role colors
    adventurer: createAgentTexture(app, 0x44aaff, 'agent_adventurer'),
    scout: createAgentTexture(app, 0x44ff88, 'agent_scout'),
    sage: createAgentTexture(app, 0xcc88ff, 'agent_sage'),
    blacksmith: createAgentTexture(app, 0xff8844, 'agent_blacksmith'),
    alchemist: createAgentTexture(app, 0x44ffaa, 'agent_alchemist'),
    merchant: createAgentTexture(app, 0xffff44, 'agent_merchant'),
    guard: createAgentTexture(app, 0x8888cc, 'agent_guard'),
  };
}
