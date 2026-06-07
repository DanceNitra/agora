/**
 * textures.ts — procedurally generates all dungeon textures for PixiJS.
 *
 * Uses Canvas2D to generate textures — all dungeon art is code-generated.
 */

import { Texture } from 'pixi.js';

// Cache so we generate once
const cache = new Map<string, Texture>();

function generateTexture(
  key: string,
  w: number,
  h: number,
  draw: (ctx: CanvasRenderingContext2D) => void,
): Texture {
  if (cache.has(key)) return cache.get(key)!;

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;

  draw(ctx);

  const texture = Texture.from(canvas);
  cache.set(key, texture);
  return texture;
}

// ── Colour helpers ──
function rgba(hex: number, alpha: number = 1) {
  const r = (hex >> 16) & 0xff;
  const g = (hex >> 8) & 0xff;
  const b = hex & 0xff;
  return `rgba(${r},${g},${b},${alpha})`;
}

// ── Floor tile ──
export function floorTexture(): Texture {
  return generateTexture('floor', 32, 32, (ctx) => {
    // Random stone variation (different shades per tile)
    const baseColors = ['#2a2a3a', '#2e2e40', '#262638', '#303046', '#282840'];
    const baseColor = baseColors[Math.floor(Math.random() * baseColors.length)];
    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, 32, 32);

    // Subtle noisy stone grain
    for (let i = 0; i < 30; i++) {
      const x = Math.random() * 32;
      const y = Math.random() * 32;
      ctx.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)';
      ctx.fillRect(x, y, 4, 4);
    }

    // Stone slab outline (individual stones, not grid)
    ctx.strokeStyle = '#1a1a28';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5;

    // Random stone crack pattern
    ctx.beginPath();
    if (Math.random() > 0.4) {
      ctx.moveTo(0, Math.random() * 32);
      ctx.lineTo(32, Math.random() * 32);
    }
    if (Math.random() > 0.4) {
      ctx.moveTo(Math.random() * 32, 0);
      ctx.lineTo(Math.random() * 32, 32);
    }
    ctx.stroke();

    // Sub-tile cracks
    ctx.strokeStyle = '#151522';
    ctx.lineWidth = 0.5;
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    for (let i = 0; i < 3; i++) {
      const sx = Math.random() * 32;
      const sy = Math.random() * 32;
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + (Math.random() - 0.5) * 16, sy + (Math.random() - 0.5) * 16);
    }
    ctx.stroke();

    // Edge highlights (top-left light source)
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, 0); ctx.lineTo(32, 0);
    ctx.moveTo(0, 0); ctx.lineTo(0, 32);
    ctx.stroke();

    // Edge shadows (bottom-right)
    ctx.strokeStyle = 'rgba(0,0,0,0.08)';
    ctx.beginPath();
    ctx.moveTo(0, 31); ctx.lineTo(32, 31);
    ctx.moveTo(31, 0); ctx.lineTo(31, 32);
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
}

// ── Wall tile ──
export function wallTexture(): Texture {
  return generateTexture('wall', 32, 32, (ctx) => {
    // Dark stone base
    ctx.fillStyle = '#3a3a50';
    ctx.fillRect(0, 0, 32, 32);

    // Subtle noise
    for (let i = 0; i < 20; i++) {
      ctx.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.03)';
      ctx.fillRect(Math.random() * 32, Math.random() * 32, 5, 5);
    }

    // Individual bricks with 3D bevel effect
    const bricks = [
      { x: 0, y: 0, w: 15, h: 7 },
      { x: 17, y: 0, w: 15, h: 7 },
      { x: 8, y: 8, w: 15, h: 7 },
      { x: 0, y: 16, w: 15, h: 7 },
      { x: 17, y: 16, w: 15, h: 7 },
      { x: 8, y: 24, w: 15, h: 7 },
    ];

    for (const brick of bricks) {
      // Base brick color (random warm variation)
      const r = Math.floor(55 + Math.random() * 20);
      const g = Math.floor(45 + Math.random() * 15);
      const b = Math.floor(65 + Math.random() * 20);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(brick.x + 1, brick.y + 1, brick.w - 2, brick.h - 2);

      // Top highlight
      ctx.fillStyle = `rgba(255,255,255,0.08)`;
      ctx.fillRect(brick.x + 1, brick.y + 1, brick.w - 2, 1);

      // Left highlight
      ctx.fillStyle = `rgba(255,255,255,0.05)`;
      ctx.fillRect(brick.x + 1, brick.y + 1, 1, brick.h - 2);

      // Bottom shadow
      ctx.fillStyle = `rgba(0,0,0,0.1)`;
      ctx.fillRect(brick.x + 1, brick.y + brick.h - 2, brick.w - 2, 1);

      // Right shadow
      ctx.fillStyle = `rgba(0,0,0,0.08)`;
      ctx.fillRect(brick.x + brick.w - 2, brick.y + 1, 1, brick.h - 2);
    }

    // Mortar lines
    ctx.strokeStyle = '#252540';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.8;
    ctx.beginPath();
    ctx.moveTo(0, 7); ctx.lineTo(32, 7);
    ctx.moveTo(0, 15); ctx.lineTo(32, 15);
    ctx.moveTo(0, 23); ctx.lineTo(32, 23);
    ctx.moveTo(15, 0); ctx.lineTo(15, 7);
    ctx.moveTo(7, 8); ctx.lineTo(7, 15);
    ctx.moveTo(23, 8); ctx.lineTo(23, 15);
    ctx.moveTo(15, 16); ctx.lineTo(15, 23);
    ctx.moveTo(7, 24); ctx.lineTo(7, 31);
    ctx.moveTo(23, 24); ctx.lineTo(23, 31);
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Top overall light sweep
    ctx.fillStyle = 'rgba(255,255,255,0.04)';
    ctx.fillRect(0, 0, 32, 4);

    // Bottom overall shadow
    ctx.fillStyle = 'rgba(0,0,0,0.06)';
    ctx.fillRect(0, 28, 32, 4);
  });
}

// ── Door tile ──
export function doorTexture(): Texture {
  return generateTexture('door', 32, 32, (ctx) => {
    ctx.fillStyle = '#6b3a2a';
    ctx.fillRect(0, 0, 32, 32);

    ctx.fillStyle = '#7a4430';
    ctx.fillRect(2, 1, 12, 30);
    ctx.fillRect(18, 1, 12, 30);

    // Plank gap
    ctx.strokeStyle = '#4a2a1a';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(15, 0); ctx.lineTo(15, 32);
    ctx.stroke();

    // Iron bands
    ctx.fillStyle = '#555577';
    ctx.fillRect(0, 6, 32, 4);
    ctx.fillRect(0, 22, 32, 4);

    // Rivets
    ctx.fillStyle = '#8888aa';
    ctx.beginPath();
    ctx.arc(4, 8, 1.5, 0, Math.PI * 2);
    ctx.arc(16, 8, 1.5, 0, Math.PI * 2);
    ctx.arc(28, 8, 1.5, 0, Math.PI * 2);
    ctx.arc(4, 24, 1.5, 0, Math.PI * 2);
    ctx.arc(16, 24, 1.5, 0, Math.PI * 2);
    ctx.arc(28, 24, 1.5, 0, Math.PI * 2);
    ctx.fill();

    // Handle
    ctx.fillStyle = '#cccc88';
    ctx.beginPath();
    ctx.arc(26, 16, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#aaaa66';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
}

// ── Torch ──
export function torchTexture(): Texture {
  return generateTexture('torch', 16, 32, (ctx) => {
    // Bracket
    ctx.fillStyle = '#444455';
    ctx.fillRect(5, 14, 6, 12);
    // Flame
    ctx.fillStyle = '#ff6600';
    ctx.beginPath();
    ctx.arc(8, 6, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffaa00';
    ctx.beginPath();
    ctx.arc(8, 5, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffeecc';
    ctx.beginPath();
    ctx.arc(8, 4, 2, 0, Math.PI * 2);
    ctx.fill();
  });
}

// ── Pillar ──
export function pillarTexture(): Texture {
  return generateTexture('pillar', 20, 32, (ctx) => {
    ctx.fillStyle = '#555566';
    ctx.fillRect(2, 28, 16, 4);
    ctx.fillStyle = '#666677';
    ctx.fillRect(5, 4, 10, 24);
    ctx.strokeStyle = '#888899';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.moveTo(6, 4); ctx.lineTo(6, 28);
    ctx.stroke();
    ctx.fillStyle = '#555566';
    ctx.fillRect(0, 0, 20, 4);
    ctx.fillStyle = '#777788';
    ctx.fillRect(2, 0, 16, 2);
    ctx.globalAlpha = 1;
  });
}

// ── Rug ──
export function rugTexture(): Texture {
  return generateTexture('rug', 48, 32, (ctx) => {
    ctx.fillStyle = '#882244';
    ctx.fillRect(0, 4, 48, 24);
    ctx.strokeStyle = '#cc6644';
    ctx.lineWidth = 2;
    ctx.strokeRect(2, 6, 44, 20);
    ctx.strokeStyle = '#aa3355';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.8;
    ctx.beginPath();
    ctx.moveTo(4, 16); ctx.lineTo(44, 16);
    ctx.moveTo(24, 8); ctx.lineTo(24, 24);
    ctx.stroke();
    // Diamond
    ctx.fillStyle = 'rgba(204,102,68,0.6)';
    ctx.beginPath();
    ctx.moveTo(24, 10); ctx.lineTo(18, 16); ctx.lineTo(30, 16);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(24, 22); ctx.lineTo(18, 16); ctx.lineTo(30, 16);
    ctx.fill();
    ctx.fillStyle = '#662233';
    ctx.fillRect(0, 0, 48, 4);
    ctx.fillRect(0, 28, 48, 4);
    ctx.globalAlpha = 1;
  });
}

// ── Chest ──
export function chestTexture(): Texture {
  return generateTexture('chest', 24, 20, (ctx) => {
    ctx.fillStyle = '#8b5e3c';
    ctx.fillRect(2, 6, 20, 14);
    ctx.fillStyle = '#7a4d2b';
    ctx.fillRect(1, 2, 22, 6);
    ctx.strokeStyle = '#aa7a55';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(2, 2); ctx.lineTo(22, 2);
    ctx.stroke();
    ctx.fillStyle = '#888899';
    ctx.fillRect(4, 6, 3, 14);
    ctx.fillRect(17, 6, 3, 14);
    ctx.fillStyle = '#ffcc44';
    ctx.beginPath();
    ctx.arc(12, 12, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ccaa33';
    ctx.fillRect(11, 10, 2, 4);
    ctx.fillStyle = '#aaaabb';
    ctx.beginPath();
    ctx.arc(12, 3, 1.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  });
}

// ── Bookshelf ──
export function bookshelfTexture(): Texture {
  return generateTexture('bookshelf', 24, 32, (ctx) => {
    ctx.fillStyle = '#5a3a2a';
    ctx.fillRect(0, 0, 24, 32);
    // Shelves
    ctx.fillStyle = '#6b4a3a';
    ctx.fillRect(0, 0, 24, 3);
    ctx.fillRect(0, 10, 24, 3);
    ctx.fillRect(0, 20, 24, 3);
    // Books
    const colors = ['#cc4444','#44cc44','#4444cc','#cccc44','#cc44cc','#44cccc'];
    for (let s = 0; s < 3; s++) {
      const by = s * 10 + 3;
      for (let bx = 2; bx < 22; bx += 5) {
        ctx.fillStyle = colors[(s + bx) % colors.length];
        ctx.fillRect(bx, by, 3, 7);
      }
    }
  });
}

// ── Table ──
export function tableTexture(): Texture {
  return generateTexture('table', 28, 20, (ctx) => {
    ctx.fillStyle = '#6b4a2a';
    ctx.fillRect(0, 0, 28, 4);
    ctx.fillStyle = '#5a3a1a';
    ctx.fillRect(0, 4, 28, 16);
    ctx.fillStyle = '#7a5a3a';
    ctx.fillRect(10, 14, 3, 6);
    ctx.fillRect(18, 14, 3, 6);
    ctx.strokeStyle = '#8a6a4a';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    ctx.moveTo(0, 0); ctx.lineTo(28, 0);
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
}

// ── Tomb ──
export function tombTexture(): Texture {
  return generateTexture('tomb', 20, 16, (ctx) => {
    ctx.fillStyle = '#555566';
    ctx.fillRect(2, 4, 16, 12);
    ctx.fillStyle = '#666677';
    ctx.fillRect(4, 0, 12, 6);
    ctx.fillStyle = '#444455';
    ctx.fillRect(0, 4, 20, 2);
    ctx.strokeStyle = '#777788';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.moveTo(6, 6); ctx.lineTo(6, 14);
    ctx.moveTo(14, 6); ctx.lineTo(14, 14);
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
}

// ── Treasure pile ──
export function treasureTexture(): Texture {
  return generateTexture('treasure', 20, 16, (ctx) => {
    ctx.fillStyle = '#664400';
    ctx.beginPath();
    ctx.ellipse(10, 12, 10, 6, 0, 0, Math.PI * 2);
    ctx.fill();
    // Coins
    const golds = ['#ffcc44', '#ffaa22', '#ffdd66', '#ccaa33'];
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = golds[i % golds.length];
      ctx.beginPath();
      ctx.arc(6 + Math.random() * 8, 8 + Math.random() * 6, 2 + Math.random() * 2, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}

// ── Workstations ──
export function anvilTexture(): Texture {
  return generateTexture('anvil', 28, 24, (ctx) => {
    ctx.fillStyle = '#3a3a4a';
    ctx.fillRect(4, 16, 20, 8);
    ctx.fillStyle = '#555568';
    ctx.fillRect(6, 8, 16, 8);
    ctx.fillStyle = '#66667a';
    ctx.fillRect(4, 4, 20, 6);
    ctx.fillStyle = '#8888aa';
    ctx.fillRect(6, 4, 16, 2);
    ctx.fillStyle = '#555568';
    ctx.beginPath();
    ctx.moveTo(4, 4); ctx.lineTo(4, 10); ctx.lineTo(0, 8);
    ctx.fill();
    ctx.strokeStyle = '#2a2a3a';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    ctx.moveTo(4, 16); ctx.lineTo(24, 16);
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
}

export function cauldronTexture(): Texture {
  return generateTexture('cauldron', 28, 26, (ctx) => {
    ctx.fillStyle = '#3a3a4a';
    ctx.beginPath();
    ctx.arc(14, 14, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#555568';
    ctx.fillRect(4, 2, 20, 4);
    ctx.fillStyle = '#66667a';
    ctx.fillRect(6, 2, 16, 2);
    ctx.fillStyle = 'rgba(34,170,68,0.7)';
    ctx.beginPath();
    ctx.arc(14, 14, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(68,221,102,0.5)';
    ctx.beginPath();
    ctx.arc(12, 12, 3, 0, Math.PI * 2);
    ctx.arc(17, 15, 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#3a3a4a';
    ctx.fillRect(4, 22, 4, 4);
    ctx.fillRect(20, 22, 4, 4);
  });
}

export function counterTexture(): Texture {
  return generateTexture('counter', 32, 22, (ctx) => {
    ctx.fillStyle = '#6b4a2a';
    ctx.fillRect(0, 0, 32, 6);
    ctx.fillStyle = '#5a3a1a';
    ctx.fillRect(0, 6, 32, 16);
    ctx.fillStyle = '#7a5a3a';
    ctx.fillRect(2, 6, 3, 16);
    ctx.strokeStyle = '#8a6a4a';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    ctx.moveTo(0, 0); ctx.lineTo(32, 0);
    ctx.moveTo(2, 6); ctx.lineTo(2, 22);
    ctx.stroke();
    ctx.globalAlpha = 1;
  });
}

// ── Agent sprites ──
function generateAgentTexture(key: string, bodyColor: string, highlight: string, hair: string): Texture {
  return generateTexture(key, 20, 28, (ctx) => {
    // Boots
    ctx.fillStyle = '#443322';
    ctx.fillRect(4, 22, 5, 6);
    ctx.fillRect(11, 22, 5, 6);
    // Legs
    ctx.fillStyle = '#554433';
    ctx.fillRect(5, 16, 4, 6);
    ctx.fillRect(11, 16, 4, 6);
    // Body
    ctx.fillStyle = bodyColor;
    ctx.fillRect(4, 7, 12, 11);
    ctx.fillStyle = highlight;
    ctx.fillRect(6, 9, 8, 5);
    // Arms
    ctx.fillStyle = bodyColor;
    ctx.fillRect(1, 8, 4, 9);
    ctx.fillRect(15, 8, 4, 9);
    // Hands
    ctx.fillStyle = '#ddbb99';
    ctx.beginPath();
    ctx.arc(3, 17, 2, 0, Math.PI * 2);
    ctx.arc(17, 17, 2, 0, Math.PI * 2);
    ctx.fill();
    // Head
    ctx.fillStyle = '#ddbb99';
    ctx.beginPath();
    ctx.arc(10, 4, 5, 0, Math.PI * 2);
    ctx.fill();
    // Hair
    ctx.fillStyle = hair;
    ctx.fillRect(6, 0, 8, 2);
    ctx.fillRect(5, 0, 10, 2);
    // Eyes
    ctx.fillStyle = '#222222';
    ctx.fillRect(7, 3, 2, 1);
    ctx.fillRect(12, 3, 2, 1);
  });
}

export function allAgentTextures(): Record<string, Texture> {
  return {
    adventurer: generateAgentTexture('agent_adventurer', '#665544', '#887766', '#553311'),
    scout: generateAgentTexture('agent_scout', '#556644', '#778866', '#444422'),
    sage: generateAgentTexture('agent_sage', '#554466', '#776688', '#442244'),
    blacksmith: generateAgentTexture('agent_blacksmith', '#665544', '#887766', '#553311'),
    alchemist: generateAgentTexture('agent_alchemist', '#554466', '#776688', '#442244'),
    merchant: generateAgentTexture('agent_merchant', '#556644', '#778866', '#444422'),
    guard: generateAgentTexture('agent_guard', '#444455', '#666677', '#222233'),
  };
}

// ── Generate ALL textures at once ──
export function generateAllTextures(): Record<string, Texture> {
  return {
    floor: floorTexture(),
    wall: wallTexture(),
    door: doorTexture(),
    torch: torchTexture(),
    pillar: pillarTexture(),
    rug: rugTexture(),
    chest: chestTexture(),
    bookshelf: bookshelfTexture(),
    table: tableTexture(),
    tomb: tombTexture(),
    treasure: treasureTexture(),
    anvil: anvilTexture(),
    cauldron: cauldronTexture(),
    counter: counterTexture(),
    ...allAgentTextures(),
  };
}
