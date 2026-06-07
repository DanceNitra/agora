/**
 * lighting.ts — dungeon lighting system with glow and bloom.
 *
 * Architecture:
 *   1. Ambient darkness overlay (70% opacity) covering the whole canvas
 *   2. Light sprites (radial gradient circles) on top with BlendMode.ADD
 *   3. GlowFilter on torch sprites for flickering flame
 *   4. AdvancedBloomFilter on the dungeon stage for atmosphere
 *
 * The effect: dark dungeon with warm torch glow bleeding into the environment.
 */

import { Container, Sprite, Texture, Graphics, Application } from 'pixi.js';
import { AdvancedBloomFilter, GlowFilter } from 'pixi-filters';
import { useWorldStore, RoomLight, TILE } from '../state/world';

// ── Config ──
const AMBIENT_ALPHA = 0.50; // 0 = full bright, 1 = full dark
const LIGHT_BLEND = 'add' as const;

// ── Generate a radial gradient light texture ──
function generateLightTexture(light: RoomLight): Texture {
  const size = light.radius * 2;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  const r = (light.color >> 16) & 0xff;
  const g = (light.color >> 8) & 0xff;
  const b = light.color & 0xff;

  // Radial gradient: bright center → transparent edge
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);

  // Inner glow
  const innerIntensity = Math.min(1, light.intensity * 1.2);
  gradient.addColorStop(0, `rgba(${r},${g},${b},${innerIntensity})`);
  gradient.addColorStop(0.15, `rgba(${r},${g},${b},${innerIntensity * 0.8})`);
  gradient.addColorStop(0.4, `rgba(${r},${g},${b},${innerIntensity * 0.4})`);
  gradient.addColorStop(0.7, `rgba(${r},${g},${b},${innerIntensity * 0.1})`);
  gradient.addColorStop(1, `rgba(${r},${g},${b},0)`);

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  return Texture.from(canvas);
}

// ── Build the lighting layer ──
export function buildLighting(parent: Container, app: Application): void {
  const state = useWorldStore.getState();

  // 1. Ambient darkness overlay
  const darkOverlay = new Graphics();
  darkOverlay.beginFill(0x000011, AMBIENT_ALPHA);
  darkOverlay.drawRect(0, 0, app.screen.width, app.screen.height);
  darkOverlay.endFill();
  parent.addChild(darkOverlay);

  // 2. Light sprites on top of darkness
  for (const light of state.lights) {
    const tex = generateLightTexture(light);
    const sprite = new Sprite(tex);
    sprite.anchor.set(0.5);
    sprite.position.set(light.x, light.y);
    sprite.blendMode = LIGHT_BLEND;
    sprite.alpha = Math.min(1, light.intensity);
    parent.addChild(sprite);
  }

  // 3. Resize handler (keep dark overlay covering the canvas)
  app.renderer.on('resize', () => {
    darkOverlay.clear();
    darkOverlay.beginFill(0x000011, AMBIENT_ALPHA);
    darkOverlay.drawRect(0, 0, app.screen.width, app.screen.height);
    darkOverlay.endFill();
  });

  // Store references for ticker animation
  (parent as any).__lights = state.lights;
}

// ── Apply GlowFilter to torch sprites ──
export function applyTorchGlow(torchContainer: Container): void {
  const glow = new GlowFilter({
    distance: 24,
    outerStrength: 2.5,
    innerStrength: 1,
    color: 0xff6622,
    quality: 0.5,
  });
  torchContainer.filters = [glow];
}

// ── Apply AdvancedBloom to entire dungeon stage ──
export function applyStageBloom(dungeonContainer: Container): void {
  const bloom = new AdvancedBloomFilter({
    bloomScale: 0.6,
    brightness: 0.8,
    blur: 8,
    quality: 6,
  });
  dungeonContainer.filters = [bloom];
}

// ── Tick: animate torch flicker ──
let flickerTime = 0;

export function tickLighting(lightContainer: Container): void {
  flickerTime += 0.02;

  // Animate child sprites (the light sprites) with subtle flicker
  for (let i = 0; i < lightContainer.children.length; i++) {
    const child = lightContainer.children[i];
    if (child instanceof Sprite && child.blendMode === LIGHT_BLEND) {
      // Sinusoidal flicker per light
      const phase = i * 1.7;
      const flicker = 0.85 + 0.15 * Math.sin(flickerTime * 3 + phase);
      child.alpha = Math.min(1, (child as any).__baseAlpha ?? child.alpha) * flicker;
    }
  }
}
