/**
 * tilemap.ts — renders the dungeon tilemap from world.ts grid.
 * Reads the 2D array and creates Sprite tiles from generated textures.
 */

import { Container, Sprite, Texture } from 'pixi.js';
import { TILE, DUNGEON_MAP } from '../state/world';

interface TileTextures {
  floor: Texture;
  wall: Texture;
  door: Texture;
}

export function buildTilemap(container: Container, textures: TileTextures): void {
  const map = DUNGEON_MAP;

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
}
