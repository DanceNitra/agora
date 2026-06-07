/**
 * particles.ts — particle system for atmosphere (torch sparks, dust motes).
 *
 * Lightweight emitter. No external dependencies. Runs in the PixiJS ticker.
 */

import { Container, Sprite, Texture } from 'pixi.js';
import { TILE } from '../state/world';

// ── Particle types ──
interface Particle {
  sprite: Sprite;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  startAlpha: number;
  startScale: number;
}

type ParticleSource = { x: number; y: number };

// ── Spark texture (tiny bright dot) ──
let sparkTexture: Texture | null = null;
let dustTexture: Texture | null = null;

function getSparkTexture(): Texture {
  if (sparkTexture) return sparkTexture;
  const canvas = document.createElement('canvas');
  canvas.width = 8;
  canvas.height = 8;
  const ctx = canvas.getContext('2d')!;
  const g = ctx.createRadialGradient(4, 4, 0, 4, 4, 4);
  g.addColorStop(0, 'rgba(255,200,150,1)');
  g.addColorStop(0.4, 'rgba(255,150,80,0.6)');
  g.addColorStop(1, 'rgba(255,100,50,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 8, 8);
  sparkTexture = Texture.from(canvas);
  return sparkTexture;
}

function getDustTexture(): Texture {
  if (dustTexture) return dustTexture;
  const canvas = document.createElement('canvas');
  canvas.width = 12;
  canvas.height = 12;
  const ctx = canvas.getContext('2d')!;
  const g = ctx.createRadialGradient(6, 6, 0, 6, 6, 6);
  g.addColorStop(0, 'rgba(200,200,220,0.4)');
  g.addColorStop(1, 'rgba(200,200,220,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 12, 12);
  dustTexture = Texture.from(canvas);
  return dustTexture;
}

// ── Spawn a spark particle from a torch position ──
function spawnSpark(container: Container, source: ParticleSource, particles: Particle[]): void {
  const sprite = new Sprite(getSparkTexture());
  sprite.anchor.set(0.5);
  sprite.position.set(
    source.x + (Math.random() - 0.5) * 6,
    source.y - 4 + Math.random() * 4,
  );
  sprite.scale.set(0.5 + Math.random() * 0.8);
  sprite.alpha = 0.8 + Math.random() * 0.2;
  container.addChild(sprite);

  particles.push({
    sprite,
    vx: (Math.random() - 0.5) * 0.5,
    vy: -(0.3 + Math.random() * 0.8), // float upward
    life: 40 + Math.random() * 60,
    maxLife: 40 + Math.random() * 60,
    startAlpha: sprite.alpha,
    startScale: sprite.scale.x,
  });
}

// ── Spawn a dust mote ──
function spawnDust(container: Container, bounds: { w: number; h: number }, particles: Particle[]): void {
  const sprite = new Sprite(getDustTexture());
  sprite.anchor.set(0.5);
  sprite.position.set(
    Math.random() * bounds.w,
    Math.random() * bounds.h,
  );
  sprite.scale.set(0.5 + Math.random() * 1.5);
  sprite.alpha = 0.1 + Math.random() * 0.3;
  container.addChild(sprite);

  particles.push({
    sprite,
    vx: (Math.random() - 0.5) * 0.15,
    vy: -(0.02 + Math.random() * 0.04),
    life: 300 + Math.random() * 400,
    maxLife: 300 + Math.random() * 400,
    startAlpha: sprite.alpha,
    startScale: sprite.scale.x,
  });
}

// ── Particle System ──
export class ParticleSystem {
  private container: Container;
  private sparks: Particle[] = [];
  private dust: Particle[] = [];
  private torchSources: ParticleSource[];
  private bounds: { w: number; h: number };
  private frameCount = 0;

  constructor(parent: Container, mapW: number, mapH: number) {
    this.container = new Container();
    parent.addChild(this.container);

    // Torch positions from the new map layout
    this.torchSources = [
      // Entrance
      { x: 4 * TILE, y: 1 * TILE },
      { x: 4 * TILE, y: 3 * TILE },
      // Grand Hall
      { x: 10 * TILE, y: 4 * TILE },
      { x: 28 * TILE, y: 4 * TILE },
      { x: 14 * TILE, y: 10 * TILE },
      { x: 24 * TILE, y: 10 * TILE },
      { x: 10 * TILE, y: 17 * TILE },
      { x: 28 * TILE, y: 17 * TILE },
      // Tavern
      { x: 4 * TILE, y: 7 * TILE },
      // Library
      { x: 34 * TILE, y: 2 * TILE },
      // Treasury
      { x: 34 * TILE, y: 8 * TILE },
      // Crypt
      { x: 34 * TILE, y: 14 * TILE },
      // Armory
      { x: 4 * TILE, y: 14 * TILE },
    ];

    this.bounds = { w: mapW * TILE, h: mapH * TILE };

    // Seed initial dust
    for (let i = 0; i < 15; i++) {
      spawnDust(this.container, this.bounds, this.dust);
    }
  }

  tick(): void {
    this.frameCount++;

    // Spawn new sparks every 3-4 frames
    if (this.frameCount % 3 === 0) {
      const src = this.torchSources[Math.floor(Math.random() * this.torchSources.length)];
      spawnSpark(this.container, src, this.sparks);
    }

    // Spawn new dust every 10 frames
    if (this.frameCount % 10 === 0 && this.dust.length < 30) {
      spawnDust(this.container, this.bounds, this.dust);
    }

    // Update sparks
    for (let i = this.sparks.length - 1; i >= 0; i--) {
      const p = this.sparks[i];
      p.life--;
      if (p.life <= 0) {
        this.container.removeChild(p.sprite);
        p.sprite.destroy();
        this.sparks.splice(i, 1);
        continue;
      }

      const t = 1 - p.life / p.maxLife; // 0..1
      p.sprite.position.x += p.vx;
      p.sprite.position.y += p.vy;
      p.vy += 0.005; // gravity
      p.sprite.alpha = p.startAlpha * (1 - t);
      p.sprite.scale.set(p.startScale * (1 - t * 0.5));
    }

    // Update dust
    for (let i = this.dust.length - 1; i >= 0; i--) {
      const p = this.dust[i];
      p.life--;
      if (p.life <= 0) {
        this.container.removeChild(p.sprite);
        p.sprite.destroy();
        this.dust.splice(i, 1);
        continue;
      }

      p.sprite.position.x += p.vx + Math.sin(this.frameCount * 0.01 + i) * 0.05;
      p.sprite.position.y += p.vy;

      // Wrap around
      if (p.sprite.position.x < 0) p.sprite.position.x = this.bounds.w;
      if (p.sprite.position.x > this.bounds.w) p.sprite.position.x = 0;
      if (p.sprite.position.y < 0) p.sprite.position.y = this.bounds.h;
      if (p.sprite.position.y > this.bounds.h) p.sprite.position.y = 0;

      // Subtle alpha pulse
      p.sprite.alpha = p.startAlpha * (0.6 + 0.4 * Math.sin(this.frameCount * 0.02 + i * 1.5));
    }
  }

  destroy(): void {
    for (const p of [...this.sparks, ...this.dust]) {
      this.container.removeChild(p.sprite);
      p.sprite.destroy();
    }
    this.sparks = [];
    this.dust = [];
    this.container.destroy();
  }
}
