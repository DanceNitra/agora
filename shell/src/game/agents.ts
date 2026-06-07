/**
 * agents.ts — renders agent sprites with smooth tweened movement.
 *
 * Each agent is a Container: [Sprite (colored avatar)] + [Text (name)].
 * The ticker lerps the visual position toward the logical position from world.ts.
 */

import { Container, Sprite, Text, Texture } from 'pixi.js';
import { useWorldStore, AgentView, TILE } from '../state/world';
import { allAgentTextures } from './textures';

// ── Smoothing factor (lower = smoother but slower to arrive) ──
const LERP = 0.08;
const SNAP_DIST = 0.5; // px — snap when close enough

// ── Per-agent visual state ──
interface AgentVisual {
  container: Container;
  sprite: Sprite;
  label: Text;
  currentX: number;
  currentY: number;
}

const visualMap = new Map<string, AgentVisual>();

// ── Nameplate style ──
const LABEL_STYLE = {
  fontFamily: 'monospace',
  fontSize: 9,
  fill: '#ccccdd',
  stroke: '#111122',
  strokeThickness: 2,
  align: 'center' as const,
};

// ── Bootstrap: create visual containers for all agents ──
export function buildAgents(parent: Container): void {
  const texMap = allAgentTextures();
  const agents = useWorldStore.getState().agents;

  for (const [id, agent] of Object.entries(agents)) {
    // Pick texture by role, fallback to guard
    const texture = texMap[agent.role] ?? texMap.guard;
    const sprite = new Sprite(texture);

    // Tint with agent color for team identification
    sprite.tint = agent.color;
    sprite.anchor.set(0.5);
    sprite.position.set(0, -2); // offset so feet align with pos

    // Name label
    const label = new Text({
      text: agent.name,
      style: LABEL_STYLE,
    });
    label.anchor.set(0.5);
    label.position.set(0, 18);

    // Container
    const container = new Container();
    container.addChild(sprite);
    container.addChild(label);

    // Position
    const [px, py] = agent.pos;
    container.position.set(px, py);

    parent.addChild(container);

    visualMap.set(id, {
      container,
      sprite,
      label,
      currentX: px,
      currentY: py,
    });
  }
}

// ── Tick: smooth movement tween ──
export function tickAgents(): void {
  const agents = useWorldStore.getState().agents;

  for (const [id, agent] of Object.entries(agents)) {
    const vis = visualMap.get(id);
    if (!vis) continue;

    let [tx, ty] = agent.pos;
    const target = agent.target;

    // If has a target, tween toward it
    if (target) {
      [tx, ty] = target;
    }

    // Lerp
    const dx = tx - vis.currentX;
    const dy = ty - vis.currentY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist > SNAP_DIST) {
      vis.currentX += dx * LERP;
      vis.currentY += dy * LERP;
    } else {
      // Snap when close enough
      vis.currentX = tx;
      vis.currentY = ty;
    }

    vis.container.position.set(vis.currentX, vis.currentY);

    // Flip sprite based on movement direction
    if (dx < -1) {
      vis.sprite.scale.x = -1;
    } else if (dx > 1) {
      vis.sprite.scale.x = 1;
    }

    // Update label with status
    vis.label.text = agent.status !== 'idle'
      ? `${agent.name}\n${agent.status}`
      : agent.name;
  }
}

// ── Cleanup ──
export function destroyAgents(): void {
  visualMap.clear();
}
