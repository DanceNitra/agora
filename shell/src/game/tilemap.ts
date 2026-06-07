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
  // Entrance hall pillars
  { tx: 2, ty: 1, key: 'pillar' },
  { tx: 6, ty: 1, key: 'pillar' },

  // Grand Hall pillars (center)
  { tx: 18, ty: 8, key: 'pillar' },
  { tx: 20, ty: 8, key: 'pillar' },
  { tx: 18, ty: 12, key: 'pillar' },
  { tx: 20, ty: 12, key: 'pillar' },

  // Grand Hall — rug in center
  { tx: 19, ty: 10, key: 'rug' },

  // Library bookshelves
  { tx: 33, ty: 1, key: 'bookshelf' },
  { tx: 36, ty: 1, key: 'bookshelf' },
  { tx: 33, ty: 2, key: 'bookshelf' },
  { tx: 36, ty: 2, key: 'bookshelf' },
  { tx: 35, ty: 1, key: 'table' },

  // Treasury
  { tx: 33, ty: 7, key: 'chest' },
  { tx: 36, ty: 7, key: 'chest' },
  { tx: 34, ty: 8, key: 'treasure' },
  { tx: 35, ty: 8, key: 'treasure' },

  // Crypt tombs
  { tx: 33, ty: 14, key: 'tomb' },
  { tx: 35, ty: 14, key: 'tomb' },
  { tx: 34, ty: 16, key: 'tomb' },
  { tx: 33, ty: 15, key: 'chest' },

  // Armory
  { tx: 2, ty: 14, key: 'anvil' },
  { tx: 6, ty: 14, key: 'table' },
  { tx: 3, ty: 13, key: 'chest' },

  // Tavern
  { tx: 6, ty: 8, key: 'table' },
  { tx: 2, ty: 8, key: 'table' },

  // Entrance counter
  { tx: 3, ty: 2, key: 'counter' },

  // Crypt cauldron
  { tx: 35, ty: 13, key: 'cauldron' },

  // Wall torches
  { tx: 10, ty: 4, key: 'torch' },
  { tx: 28, ty: 4, key: 'torch' },
  { tx: 10, ty: 17, key: 'torch' },
  { tx: 28, ty: 17, key: 'torch' },
  { tx: 14, ty: 10, key: 'torch' },
  { tx: 24, ty: 10, key: 'torch' },
  { tx: 1, ty: 4, key: 'torch' },
  { tx: 1, ty: 10, key: 'torch' },
  { tx: 38, ty: 4, key: 'torch' },
  { tx: 38, ty: 10, key: 'torch' },
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
