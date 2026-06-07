/**
 * tilemap.ts — renders the dungeon tilemap from world.ts grid + decorations.
 * Reads the 2D array and creates Sprite tiles from generated textures.
 * Also adds decorative sprites (pillars, rugs, chests, etc.) at fixed positions.
 */

import { Container, Sprite, Texture } from 'pixi.js';
import { TILE, DUNGEON_MAP, useWorldStore } from '../state/world';

interface TileTextures {
  floor: Texture;
  wall: Texture;
  door: Texture;
}

interface DecorTextures {
  pillar: Texture;
  rug: Texture;
  chest: Texture;
  bookshelf: Texture;
  table: Texture;
  tomb: Texture;
  treasure: Texture;
  anvil: Texture;
  cauldron: Texture;
  counter: Texture;
  torch: Texture;
}

// ── Decoration positions (tile coords) ──
const DECORATIONS: { tx: number; ty: number; key: keyof DecorTextures; tint?: number }[] = [
  // Pillars (corners of the main hall)
  { tx: 6, ty: 4, key: 'pillar' },
  { tx: 6, ty: 16, key: 'pillar' },
  { tx: 16, ty: 4, key: 'pillar' },
  { tx: 16, ty: 16, key: 'pillar' },

  // Library pillars
  { tx: 26, ty: 3, key: 'pillar' },
  { tx: 35, ty: 3, key: 'pillar' },
  { tx: 26, ty: 9, key: 'pillar' },
  { tx: 35, ty: 9, key: 'pillar' },

  // Crypt pillars
  { tx: 26, ty: 11, key: 'pillar' },
  { tx: 35, ty: 11, key: 'pillar' },
  { tx: 26, ty: 18, key: 'pillar' },
  { tx: 35, ty: 18, key: 'pillar' },

  // Rug (center of tavern area)
  { tx: 8, ty: 11, key: 'rug' },

  // Chests
  { tx: 34, ty: 3, key: 'chest' },
  { tx: 28, ty: 17, key: 'chest' },
  { tx: 6, ty: 2, key: 'chest' },

  // Bookshelves in library
  { tx: 27, ty: 3, key: 'bookshelf' },
  { tx: 34, ty: 6, key: 'bookshelf' },
  { tx: 30, ty: 3, key: 'bookshelf' },

  // Tables
  { tx: 10, ty: 5, key: 'table' },
  { tx: 12, ty: 5, key: 'table' },
  { tx: 21, ty: 3, key: 'table' },
  { tx: 22, ty: 3, key: 'table' },

  // Tombs in crypt
  { tx: 28, ty: 14, key: 'tomb' },
  { tx: 30, ty: 14, key: 'tomb' },
  { tx: 32, ty: 14, key: 'tomb' },
  { tx: 34, ty: 14, key: 'tomb' },
  { tx: 28, ty: 18, key: 'tomb' },
  { tx: 32, ty: 18, key: 'tomb' },

  // Treasure in treasury
  { tx: 29, ty: 9, key: 'treasure' },
  { tx: 30, ty: 10, key: 'treasure' },

  // Workstation items
  { tx: 3, ty: 14, key: 'anvil' },
  { tx: 20, ty: 3, key: 'cauldron' },
  { tx: 3, ty: 3, key: 'counter' },

  // Torches on walls
  { tx: 8, ty: 1, key: 'torch' },
  { tx: 14, ty: 1, key: 'torch' },
  { tx: 28, ty: 1, key: 'torch' },
  { tx: 34, ty: 1, key: 'torch' },
  { tx: 8, ty: 18, key: 'torch' },
  { tx: 14, ty: 18, key: 'torch' },
  { tx: 28, ty: 10, key: 'torch' },
  { tx: 34, ty: 10, key: 'torch' },
];

export function buildTilemap(container: Container, textures: TileTextures & DecorTextures): void {
  const map = DUNGEON_MAP;

  // Render tiles
  for (let y = 0; y < map.length; y++) {
    for (let x = 0; x < map[y].length; x++) {
      const tile = map[y][x];
      const px = x * TILE + TILE / 2;
      const py = y * TILE + TILE / 2;

      let tex: Texture;
      if (tile === 0) tex = textures.floor;
      else if (tile === 1) tex = textures.wall;
      else tex = textures.door;

      const sprite = new Sprite(tex);
      sprite.anchor.set(0.5);
      sprite.position.set(px, py);
      container.addChild(sprite);
    }
  }

  // Render decorations
  for (const dec of DECORATIONS) {
    const tex = textures[dec.key];
    if (!tex) continue;
    const sprite = new Sprite(tex);
    sprite.anchor.set(0.5);
    sprite.position.set(dec.tx * TILE + TILE / 2, dec.ty * TILE + TILE / 2);
    if (dec.tint) sprite.tint = dec.tint;
    container.addChild(sprite);
  }
}
