/**
 * HUDOverlay — player stats + quest tracker + task display + LIVE EVENT LOG (DOM).
 *
 * Connects to server WebSocket at /ws for real-time system events.
 */
export class HUDOverlay {
  private container: HTMLDivElement;
  private titleEl: HTMLDivElement;
  private statsEl: HTMLDivElement;
  private questsEl: HTMLDivElement;
  private tasksEl: HTMLDivElement;
  private logEl: HTMLDivElement;
  private visible = true;

  // Event log ring buffer
  private logEntries: string[] = [];
  private readonly MAX_LOG = 20;
  private ws: WebSocket | null = null;
  private wsConnected = false;

  constructor() {
    this.container = document.createElement('div');
    this.container.style.cssText = `
      position: fixed;
      top: 8px;
      left: 8px;
      right: 8px;
      bottom: 8px;
      z-index: 9999;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      color: #ccc;
      pointer-events: none;
      user-select: none;
      text-shadow: 0 0 4px #000, 0 0 8px #000;
      line-height: 1.5;
      display: flex;
      flex-direction: column;
    `;

    // ── TOP SECTION (fixed height) ──
    const topSection = document.createElement('div');
    topSection.style.flexShrink = '0';

    this.titleEl = document.createElement('div');
    this.titleEl.style.cssText = 'font-size: 14px; font-weight: bold; color: #88bbff; margin-bottom: 4px;';
    this.titleEl.textContent = '⚔ Agora Dungeon';

    this.statsEl = document.createElement('div');
    this.statsEl.style.marginBottom = '4px';

    this.questsEl = document.createElement('div');
    this.questsEl.style.marginBottom = '4px';

    this.tasksEl = document.createElement('div');
    this.tasksEl.style.marginBottom = '4px';

    topSection.appendChild(this.titleEl);
    topSection.appendChild(this.statsEl);
    topSection.appendChild(this.questsEl);
    topSection.appendChild(this.tasksEl);

    // ── EVENT LOG (scrollable, fills remaining space) ──
    this.logEl = document.createElement('div');
    this.logEl.style.cssText = `
      flex: 1;
      overflow-y: auto;
      margin-top: 4px;
      padding: 4px 6px;
      background: rgba(0,0,0,0.55);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 4px;
      font-size: 11px;
      min-height: 60px;
      max-height: 200px;
    `;
    this.logEl.innerHTML = '<div style="color:#555;">Connecting to event stream…</div>';

    this.container.appendChild(topSection);
    this.container.appendChild(this.logEl);
    document.body.appendChild(this.container);

    // ── Connect WebSocket ──
    this.connectWS();
  }

  private connectWS(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    try {
      this.ws = new WebSocket('ws://localhost:8000/ws');
      this.ws.onopen = () => {
        this.wsConnected = true;
        this.addLog('connected', '📡 Event stream connected');
      };
      this.ws.onclose = () => {
        this.wsConnected = false;
        this.addLog('system', '📡 Disconnected — retrying…');
        setTimeout(() => this.connectWS(), 3000);
      };
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          this.handleServerEvent(msg);
        } catch {
          // raw text message
          this.addLog('message', evt.data.slice(0, 120));
        }
      };
      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      // WebSocket not supported
    }
  }

  private handleServerEvent(msg: any): void {
    const type = msg.type || 'unknown';
    const p = msg.payload || {};

    // Colour-code and log
    const time = new Date().toLocaleTimeString();

    switch (type) {
      case 'task_posted':
        this.addLog('task', `📋 Task posted: ${p.title || '?'} (difficulty ${p.difficulty || '?'})`);
        break;
      case 'task_assigned':
        this.addLog('task', `📌 Task assigned: ${p.title || '?'} → ${p.agent_id || '?'} (${p.role || '?'})`);
        break;
      case 'task_completed':
        this.addLog('success', `✅ Task done: ${p.title || '?'} → +${p.reward_energy || 0} energy +${(p.trust_boost || 0) * 100}% trust`);
        break;
      case 'agent_died':
        this.addLog('death', `💀 Agent died: ${p.agent_id || '?'} (${p.role || '?'}) gen=${p.generation || 0}`);
        break;
      case 'agent_reborn':
        this.addLog('birth', `✨ Agent reborn: ${p.agent_id || '?'} gen=${p.new_generation || 1} energy=${p.starting_energy || 0}`);
        break;
      case 'heartbeat':
        // Only log heartbeats at unusual agent counts
        if (p.agents !== undefined) {
          this.updateWSIndicator(p.agents, p.total_energy);
        }
        break;
      case 'stigmergy_insight':
        this.addLog('info', `🧠 Stigmergy insight tick ${p.tick || '?'}`);
        break;
      case 'resource_drop':
        this.addLog('info', `💎 ${p.agent_id || '?'} found ${p.quantity || 0} ${p.resource || '?'}`);
        break;
      case 'agent_thought':
        // Only log notable thoughts (high action != wait)
        if (p.action && p.action !== 'wait' && p.action !== 'unknown') {
          this.addLog('thought', `💭 ${p.agent_id || '?'}: ${p.action} — ${(p.insight || '').slice(0, 60)}`);
        }
        break;
      default:
        if (type !== 'message') {
          this.addLog('system', `📡 ${type}: ${JSON.stringify(p).slice(0, 60)}`);
        }
    }
  }

  private addLog(category: string, text: string): void {
    const icons: Record<string, string> = {
      task: '📋', success: '✅', death: '💀', birth: '✨',
      info: 'ℹ️', thought: '💭', system: '🔧', connected: '🔗',
      message: '📨',
    };
    const colors: Record<string, string> = {
      task: '#88ccff', success: '#44ff88', death: '#ff4444', birth: '#ffdd44',
      info: '#aaaaaa', thought: '#cc88ff', system: '#888888', connected: '#44ff88',
      message: '#cccccc',
    };
    const icon = icons[category] || '•';
    const color = colors[category] || '#ccc';
    const time = new Date().toLocaleTimeString();
    const entry = `<span style="color:#666;">${time}</span> <span style="color:${color};">${icon} ${this.escapeHtml(text)}</span>`;

    this.logEntries.push(entry);
    if (this.logEntries.length > this.MAX_LOG) {
      this.logEntries.shift();
    }
    this.renderLog();
  }

  private escapeHtml(s: string): string {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  private renderLog(): void {
    this.logEl.innerHTML = this.logEntries.join('<br>');
    // Auto-scroll to bottom
    this.logEl.scrollTop = this.logEl.scrollHeight;
  }

  private updateWSIndicator(agentCount: number, totalEnergy?: number): void {
    // Update title with connection status
    const statusDot = this.wsConnected ? '🟢' : '🔴';
    const energyStr = totalEnergy !== undefined ? ` | ⚡${totalEnergy.toFixed(0)}` : '';
    this.titleEl.textContent = `⚔ Agora Dungeon ${statusDot} ${agentCount} agents${energyStr}`;
  }

  /** Toggle HUD visibility (e.g. with H key). */
  toggle(): boolean {
    this.visible = !this.visible;
    this.container.style.display = this.visible ? 'flex' : 'none';
    return this.visible;
  }

  /** Update HUD content each frame. */
  update(data: {
    playerX: number;
    playerY: number;
    nearNPCs: { name: string; health: number; objective?: string }[];
    tasks: { id: number; description: string; status: string; assignedTo?: string }[];
    quests?: { npcName: string; activeQuestTitle: string; questStatus: string }[];
  }): void {
    // Stats
    this.statsEl.innerHTML = `
      <div>📍 [${data.playerX.toFixed(0)}, ${data.playerY.toFixed(0)}]</div>
    `;

    // Active quests section
    let activeQuestHtml = '';
    if (data.quests && data.quests.length > 0) {
      for (const q of data.quests) {
        activeQuestHtml += `<div style="color:#88ff88">📜 ${q.npcName}: ${q.activeQuestTitle}</div>`;
      }
    }
    const questSection = activeQuestHtml
      ? `<div style="color:#888; margin-bottom:2px;">━━ Active Quests ━━</div>${activeQuestHtml}`
      : '';

    // Nearby NPCs
    let npcHtml = '';
    for (const npc of data.nearNPCs) {
      const hpColor = npc.health > 60 ? '#44cc44' : npc.health > 30 ? '#cccc44' : '#cc4444';
      npcHtml += `<div style="color:${hpColor}">${npc.name} ${npc.objective ? `— ${npc.objective}` : ''}</div>`;
    }
    const npcSection = npcHtml
      ? `<div style="color:#888; margin-bottom:2px;">━━ Nearby ━━</div>${npcHtml}`
      : '';

    this.questsEl.innerHTML = questSection + (questSection && npcSection ? '<br>' : '') + npcSection;

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
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.container.remove();
  }
}
