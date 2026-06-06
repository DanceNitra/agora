/**
 * GodConsole — Overlay terminal for Agora dungeon (Q3.5).
 *
 * Toggle with Backtick (`) key.
 * Commands: !spawn, !announce, !assign, !reward, !trust, !tasks, !help, !clear, !status
 */
import Phaser from 'phaser';
import { GameScene } from './scenes/GameScene';
import { LLMNPCSprite } from './npc/LLMNPCSprite';

const API_BASE = 'http://localhost:8000/api/v1/dungeon';

interface SpawnResult {
  status: string;
  agent_name: string;
  role: string;
  position: { x: number; y: number };
  color: number;
  energy_balance: number;
  trust_score: number;
}

export class GodConsole {
  public static visible: boolean = false;
  private overlay: HTMLDivElement;
  private output: HTMLDivElement;
  private input: HTMLInputElement;
  private game: Phaser.Game;
  private logLines: string[] = [];

  constructor(game: Phaser.Game) {
    this.game = game;
    this.overlay = this.createOverlay();
    this.output = this.createOutput();
    this.input = this.createInput();
    this.overlay.appendChild(this.output);
    this.overlay.appendChild(this.input);

    document.body.appendChild(this.overlay);

    // Listen for backtick key globally
    document.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === '`' || e.key === '°') {
        e.preventDefault();
        this.toggle();
      }
      if (e.key === 'Escape' && GodConsole.visible) {
        this.hide();
      }
    });

    // Handle Enter in input
    this.input.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const cmd = this.input.value.trim();
        this.input.value = '';
        if (cmd) {
          this.execute(cmd);
        }
      }
    });

    this.log('AGORA GOD CONSOLE v1.0');
    this.log('Type !help for commands. Toggle with ` (backtick).');
  }

  private createOverlay(): HTMLDivElement {
    const el = document.createElement('div');
    el.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0, 0, 0, 0.80);
      z-index: 9999;
      display: none;
      flex-direction: column;
      font-family: 'Courier New', 'Consolas', monospace;
      color: #00ff88;
      padding: 20px;
    `;
    return el;
  }

  private createOutput(): HTMLDivElement {
    const el = document.createElement('div');
    el.style.cssText = `
      flex: 1;
      overflow-y: auto;
      white-space: pre-wrap;
      font-size: 14px;
      line-height: 1.5;
      margin-bottom: 10px;
      padding: 10px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid #00ff8844;
      border-radius: 4px;
    `;
    return el;
  }

  private createInput(): HTMLInputElement {
    const el = document.createElement('input');
    el.style.cssText = `
      width: 100%;
      background: rgba(0, 0, 0, 0.7);
      border: 1px solid #00ff8866;
      color: #00ff88;
      font-family: 'Courier New', monospace;
      font-size: 16px;
      padding: 10px 14px;
      outline: none;
      border-radius: 4px;
    `;
    el.placeholder = '> type !help or a command...';
    el.autofocus = true;
    return el;
  }

  toggle(): void {
    if (GodConsole.visible) {
      this.hide();
    } else {
      this.show();
    }
  }

  show(): void {
    GodConsole.visible = true;
    this.overlay.style.display = 'flex';
    this.input.focus();
  }

  hide(): void {
    GodConsole.visible = false;
    this.overlay.style.display = 'none';
  }

  isVisible(): boolean {
    return GodConsole.visible;
  }

  private log(msg: string, color: string = '#00ff88'): void {
    const timestamp = new Date().toLocaleTimeString();
    const line = `[${timestamp}] ${msg}`;
    this.logLines.push(line);
    const entry = document.createElement('div');
    entry.textContent = line;
    entry.style.color = color;
    this.output.appendChild(entry);
    this.output.scrollTop = this.output.scrollHeight;
  }

  private async execute(cmd: string): Promise<void> {
    this.log(`> ${cmd}`, '#88ffaa');

    const parts = cmd.split(/\s+/);
    const command = parts[0].toLowerCase();

    switch (command) {
      case '!help':
        this.showHelp();
        break;
      case '!clear':
        this.output.innerHTML = '';
        this.logLines = [];
        this.log('Console cleared.');
        break;
      case '!status':
        await this.cmdStatus();
        break;
      case '!spawn':
        await this.cmdSpawn(parts);
        break;
      case '!announce':
        await this.cmdAnnounce(parts);
        break;
      case '!assign':
        await this.cmdAssign(parts);
        break;
      case '!reward':
        await this.cmdReward(parts);
        break;
      case '!trust':
        await this.cmdTrust(parts);
        break;
      case '!tasks':
        await this.cmdTasks();
        break;
      default:
        this.log(`Unknown command: ${command}. Type !help`, '#ff6666');
    }
  }

  private showHelp(): void {
    this.log('── Available Commands ──', '#ffaa44');
    this.log('  !spawn <name> <role>      Spawn new agent (explorer/warrior/mage/healer/rogue/ranger)', '#aaddff');
    this.log('  !announce <title> [diff=1] [reward=10]  Announce a task (bidding open)', '#aaddff');
    this.log('  !assign <task_id> <agent>  Assign task to best bidder or force-assign to agent', '#aaddff');
    this.log('  !reward <agent> <amount>   Reward agent with energy', '#aaddff');
    this.log('  !trust <agent>            Show trust scores for an agent', '#aaddff');
    this.log('  !tasks                    List open/assigned tasks with bids', '#aaddff');
    this.log('  !status                   Server health + agent count', '#aaddff');
    this.log('  !clear                    Clear console', '#aaddff');
    this.log('  !help                     Show this help', '#aaddff');
    this.log('  Esc / `                    Close console', '#aaddff');
  }

  private async cmdStatus(): Promise<void> {
    try {
      const r = await fetch('http://localhost:8000/api/v1/health');
      const data = await r.json();
      this.log(`Server: OK | Agents: ${data.agents} | Tick: ${data.tick}`, '#44ff44');
      // Also show config status
      const cfg = await fetch(`${API_BASE}/config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const cfgData = await cfg.json();
      this.log(`LLM enabled: ${cfgData.config?.llm_enabled ?? '?'}`, '#44ff44');
    } catch (err) {
      this.log('Server unreachable!', '#ff6666');
    }
  }

  private async cmdSpawn(parts: string[]): Promise<void> {
    if (parts.length < 3) {
      this.log('Usage: !spawn <name> <role> [x] [y]', '#ff6666');
      this.log('Roles: explorer, warrior, mage, healer, rogue, ranger', '#ff6666');
      return;
    }
    const agentName = parts[1];
    const role = parts[2];
    const x = parseInt(parts[3]) || 10;
    const y = parseInt(parts[4]) || 16;

    try {
      const r = await fetch(`${API_BASE}/spawn-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: agentName, role, agent_x: x, agent_y: y }),
      });
      const data: SpawnResult = await r.json();

      if (data.status === 'spawned') {
        // Spawn in game
        const scene = this.game.scene.getScene('GameScene') as GameScene;
        if (scene && (scene as any).spawnLLMNPC) {
          (scene as any).spawnLLMNPC(
            data.agent_name,
            data.position.x * 32,
            data.position.y * 32,
            data.color,
            `Explore the ${role}'s path`,
          );
          this.log(`✓ Spawned ${data.agent_name} (${role}) at tile (${x},${y})`, '#44ff44');
          this.log(`  Energy: ${data.energy_balance} | Trust: ${data.trust_score}`, '#88ff88');
        } else {
          this.log(`✓ Backend spawned ${data.agent_name}, but game scene not ready for visual spawn`, '#ffaa44');
        }
      } else {
        this.log(`✗ Spawn failed: ${JSON.stringify(data)}`, '#ff6666');
      }
    } catch (err) {
      this.log(`✗ Spawn error: ${err}`, '#ff6666');
    }
  }

  private async cmdAnnounce(parts: string[]): Promise<void> {
    if (parts.length < 2) {
      this.log('Usage: !announce <title> [difficulty=1] [reward=10]', '#ff6666');
      return;
    }
    const title = parts.slice(1, parts.length - 2).join(' ') || parts[1];
    const difficulty = parseInt(parts[parts.length - 2]) || 1;
    const reward = parseInt(parts[parts.length - 1]) || 10;

    try {
      const r = await fetch(`${API_BASE}/announce-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          description: `Task announced via God Console`,
          difficulty,
          reward_energy: reward,
          task_type: 'exploration',
        }),
      });
      const data = await r.json();
      if (data.status === 'task_announced') {
        this.log(`✓ Task #${data.task_id} announced: "${data.title}" (diff=${data.difficulty}, reward=${data.reward_energy})`, '#44ff44');
        this.log('  Bidding open! Agents will bid on their next tick.', '#88ff88');
      } else {
        this.log(`✗ ${JSON.stringify(data)}`, '#ff6666');
      }
    } catch (err) {
      this.log(`✗ Announce error: ${err}`, '#ff6666');
    }
  }

  private async cmdAssign(parts: string[]): Promise<void> {
    if (parts.length < 3) {
      this.log('Usage: !assign <task_id> <agent_name>', '#ff6666');
      this.log('  Assigns task to best bidder (if agent_name matches highest bid)', '#ff6666');
      return;
    }
    const taskId = parseInt(parts[1]);
    const agentName = parts[2];

    // Try assign-best first
    try {
      const r = await fetch(`${API_BASE}/assign-best/${taskId}`, { method: 'POST' });
      const data = await r.json();
      if (data.status === 'task_assigned') {
        this.log(`✓ Task #${taskId} → ${data.winner} (${data.winner_role}) bid=${data.bid_amount}`, '#44ff44');
        if (data.winner !== agentName) {
          this.log(`  Note: won by ${data.winner}, not ${agentName} (highest bid wins)`, '#ffaa44');
        }
      } else if (data.error === 'no_bids') {
        this.log(`✗ No bids on task #${taskId}. Force-assigning to ${agentName}...`, '#ffaa44');
        // Force assign via general tasks API
        try {
          // Get agent UUID
          const nameResp = await fetch(`${API_BASE}/agents`);
          // Fallback: try direct db update isn't available via API
          this.log('  Force-assign not yet supported via API. Try: !spawn to add more agents, then retry.', '#ff6666');
        } catch {
          this.log('✗ Assign error', '#ff6666');
        }
      } else {
        this.log(`✗ ${JSON.stringify(data)}`, '#ff6666');
      }
    } catch (err) {
      this.log(`✗ Assign error: ${err}`, '#ff6666');
    }
  }

  private async cmdReward(parts: string[]): Promise<void> {
    if (parts.length < 3) {
      this.log('Usage: !reward <agent_name> <amount>', '#ff6666');
      return;
    }
    const agentName = parts[1];
    const amount = parseFloat(parts[2]) || 10;

    try {
      const r = await fetch(`${API_BASE}/reward-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: agentName, amount }),
      });
      const data = await r.json();
      if (data.status === 'rewarded') {
        this.log(`✓ Rewarded ${agentName} with ${amount} energy (new balance: ${data.new_energy_balance})`, '#44ff44');
      } else {
        this.log(`✗ ${JSON.stringify(data)}`, '#ff6666');
      }
    } catch (err) {
      this.log(`✗ Reward error: ${err}`, '#ff6666');
    }
  }

  private async cmdTrust(parts: string[]): Promise<void> {
    if (parts.length < 2) {
      this.log('Usage: !trust <agent_name>', '#ff6666');
      return;
    }
    const agentName = parts[1];

    try {
      const r = await fetch(`${API_BASE}/trust?agent_name=${encodeURIComponent(agentName)}`);
      const data = await r.json();
      if (data.trust) {
        this.log(`Trust scores for ${agentName}:`, '#aaddff');
        for (const [other, score] of Object.entries(data.trust)) {
          const s = score as number;
          const color = s >= 0.6 ? '#44ff44' : s >= 0.4 ? '#ffaa44' : '#ff6666';
          this.log(`  → ${other}: ${(s * 100).toFixed(0)}%`, color);
        }
      } else {
        this.log(`No trust data for ${agentName}`, '#ffaa44');
      }
    } catch (err) {
      this.log(`✗ Trust error: ${err}`, '#ff6666');
    }
  }

  private async cmdTasks(): Promise<void> {
    try {
      const r = await fetch(`${API_BASE}/tasks`);
      const data = await r.json();
      if (data.tasks && data.tasks.length > 0) {
        this.log(`Open/assigned tasks (${data.total}):`, '#aaddff');
        for (const t of data.tasks) {
          const statusColor = t.status === 'assigned' ? '#44ff44' : '#ffaa44';
          this.log(`  #${t.id}: "${t.title}" [${t.status}] diff=${t.difficulty} reward=${t.reward_energy}`, statusColor);
          if (t.assignee) {
            this.log(`    → Assigned to: ${t.assignee}`, '#88ff88');
          }
          if (t.bids && t.bids.length > 0) {
            for (const b of t.bids) {
              this.log(`    Bid: ${b.agent_name} = ${(b.bid_amount * 100).toFixed(0)}% "${b.bid_reason}"`, '#888888');
            }
          }
        }
      } else {
        this.log('No open tasks. Use !announce to create one.', '#ffaa44');
      }
    } catch (err) {
      this.log(`✗ Tasks error: ${err}`, '#ff6666');
    }
  }
}
