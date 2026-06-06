/**
 * HUDOverlay — player stats + quest tracker + task display (DOM).
 */
export class HUDOverlay {
  private container: HTMLDivElement;
  private titleEl: HTMLDivElement;
  private statsEl: HTMLDivElement;
  private questsEl: HTMLDivElement;
  private tasksEl: HTMLDivElement;
  private visible = true;

  constructor() {
    this.container = document.createElement('div');
    this.container.style.cssText = `
      position: fixed;
      top: 8px;
      left: 8px;
      z-index: 9999;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      color: #ccc;
      pointer-events: none;
      user-select: none;
      text-shadow: 0 0 4px #000, 0 0 8px #000;
      line-height: 1.5;
    `;

    this.titleEl = document.createElement('div');
    this.titleEl.style.cssText = 'font-size: 14px; font-weight: bold; color: #88bbff; margin-bottom: 4px;';
    this.titleEl.textContent = '⚔ Agora Dungeon';

    this.statsEl = document.createElement('div');
    this.statsEl.style.marginBottom = '4px';

    this.questsEl = document.createElement('div');
    this.questsEl.style.marginBottom = '4px';

    this.tasksEl = document.createElement('div');

    this.container.appendChild(this.titleEl);
    this.container.appendChild(this.statsEl);
    this.container.appendChild(this.questsEl);
    this.container.appendChild(this.tasksEl);
    document.body.appendChild(this.container);
  }

  /** Toggle HUD visibility (e.g. with H key). */
  toggle(): boolean {
    this.visible = !this.visible;
    this.container.style.display = this.visible ? 'block' : 'none';
    return this.visible;
  }

  /** Update HUD content each frame. */
  update(data: {
    playerX: number;
    playerY: number;
    nearNPCs: { name: string; health: number; objective?: string }[];
    tasks: { id: number; description: string; status: string; assignedTo?: string }[];
  }): void {
    // Stats
    this.statsEl.innerHTML = `
      <div>📍 [${data.playerX.toFixed(0)}, ${data.playerY.toFixed(0)}]</div>
    `;

    // Quests / nearby NPCs
    let questHtml = '';
    for (const npc of data.nearNPCs) {
      const hpColor = npc.health > 60 ? '#44cc44' : npc.health > 30 ? '#cccc44' : '#cc4444';
      questHtml += `<div style="color:${hpColor}">${npc.name} ${npc.objective ? `— ${npc.objective}` : ''}</div>`;
    }
    if (questHtml) {
      this.questsEl.innerHTML = `<div style="color:#888; margin-bottom:2px;">━━ NPCs ━━</div>${questHtml}`;
    } else {
      this.questsEl.innerHTML = '';
    }

    // Tasks
    let taskHtml = '';
    for (const t of data.tasks) {
      const statusColor = t.status === 'assigned' ? '#44ff88' : t.status === 'completed' ? '#888' : '#ffcc44';
      taskHtml += `<div style="color:${statusColor}">${t.description} ${t.assignedTo ? `→ ${t.assignedTo}` : ''}</div>`;
    }
    if (taskHtml) {
      this.tasksEl.innerHTML = `<div style="color:#888; margin-bottom:2px;">━━ Tasks ━━</div>${taskHtml}`;
    } else {
      this.tasksEl.innerHTML = '';
    }
  }

  destroy(): void {
    this.container.remove();
  }
}
