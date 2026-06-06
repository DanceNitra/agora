import Phaser from 'phaser';
import { NPCSprite, NPCRole } from '../npc/NPCSprite';
import { BTNPCSprite } from '../npc/BTNPCSprite';
import { LLMNPCSprite } from '../npc/LLMNPCSprite';
import { TILE, MAP_W, MAP_H, DUNGEON_MAP } from '../config/map';
import { GodConsole } from '../GodConsole';
import { MinimapOverlay } from '../MinimapOverlay';
import { AudioManager } from '../audio/AudioManager';
import { HUDOverlay } from '../HUDOverlay';

interface Updatable { update(delta?: number): void; }

const PERSIST_API = 'http://localhost:8000/api/v1/dungeon/persist';

interface PersistedNPC {
  npc_id: string;
  npc_name: string;
  role: string;
  pos_x: number;
  pos_y: number;
  health: number;
  inventory: string[];
  status: string;
  objective: string;
}

interface PersistedQuest {
  quest_id: string;
  title: string;
  status: string;
  progress: Record<string, any>;
}

export class GameScene extends Phaser.Scene {
  private player!: Phaser.Physics.Arcade.Sprite;
  private walls!: Phaser.Physics.Arcade.StaticGroup;
  private doors!: Phaser.Physics.Arcade.StaticGroup;
  private npcs: Updatable[] = [];
  private npcSprites: Phaser.Physics.Arcade.Sprite[] = [];
  private llmNPCs: LLMNPCSprite[] = [];
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: Record<string, Phaser.Input.Keyboard.Key>;
  private playerDust!: Phaser.GameObjects.Particles.ParticleEmitter;
  private playerWalkTimer: number = 0;
  private stepTimer: number = 0;
  private playerLight!: Phaser.GameObjects.Light;
  private minimapOverlay!: MinimapOverlay;
  public audio!: AudioManager;
  private hud!: HUDOverlay;
  private persistTimer: number = 0;
  private npcQuests: Map<string, PersistedQuest[]> = new Map();

  constructor() {
    super({ key: 'GameScene' });
  }

  create(): void {
    // Load NPC state from persistence API first
    this.loadPersistedState();

    // --- LIGHTING (Q4.4) ---
    this.lights.enable().setAmbientColor(0x444466);

    // --- TILEMAP ---
    this.walls = this.physics.add.staticGroup();
    this.doors = this.physics.add.staticGroup();

    for (let y = 0; y < MAP_H; y++) {
      for (let x = 0; x < MAP_W; x++) {
        const tile = DUNGEON_MAP[y][x];
        const px = x * TILE + TILE / 2;
        const py = y * TILE + TILE / 2;

        if (tile === 0) {
          this.add.image(px, py, 'floor').setDepth(tile).setPipeline('Light2D');
        } else if (tile === 1) {
          const w = this.walls.create(px, py, 'wall') as Phaser.Physics.Arcade.Sprite;
          w.refreshBody();
          w.setPipeline('Light2D');
        } else if (tile === 2) {
          const d = this.doors.create(px, py, 'door') as Phaser.Physics.Arcade.Sprite;
          d.refreshBody();
          d.setPipeline('Light2D');
        }
      }
    }

    // --- WORKSTATIONS (Q1.5) ---
    const stations = [
      { x: 3.5 * TILE, y: 14 * TILE, texture: 'anvil', name: 'Anvil' },
      { x: 20 * TILE, y: 3 * TILE, texture: 'cauldron', name: 'Cauldron' },
      { x: 3.5 * TILE, y: 3.5 * TILE, texture: 'counter', name: 'Counter' },
    ];
    for (const s of stations) {
      this.add.image(s.x, s.y, s.texture).setDepth(s.y).setPipeline('Light2D');
    }

    // --- DECORATIVE ELEMENTS (Q4.1) ---
    // Torches
    const torches = [
      { x: 1.5 * TILE, y: 1.5 * TILE },
      { x: 22.5 * TILE, y: 1.5 * TILE },
      { x: 1.5 * TILE, y: 18.5 * TILE },
      { x: 22.5 * TILE, y: 18.5 * TILE },
    ];
    for (const t of torches) {
      this.add.image(t.x, t.y, 'torch').setDepth(t.y).setPipeline('Light2D');
    }

    // Pillars
    const pillars = [
      { x: 8 * TILE, y: 7 * TILE },
      { x: 16 * TILE, y: 7 * TILE },
      { x: 8 * TILE, y: 13 * TILE },
      { x: 16 * TILE, y: 13 * TILE },
    ];
    for (const p of pillars) {
      this.add.image(p.x, p.y, 'pillar').setDepth(p.y).setPipeline('Light2D');
    }

    // Rug in center
    this.add.image(12 * TILE, 10 * TILE, 'rug').setDepth(10 * TILE + 0.5).setPipeline('Light2D');

    // Chest
    this.add.image(1.5 * TILE, 17 * TILE, 'chest').setDepth(17 * TILE).setPipeline('Light2D');

    // --- LIGHT SOURCES ---
    // Torch lights
    for (const t of torches) {
      this.lights.addLight(t.x, t.y, 200, 0xff6622, 1.5);
    }

    // Workstation lights
    this.lights.addLight(3.5 * TILE, 14 * TILE, 140, 0xff8844, 1.0); // Anvil
    this.lights.addLight(20 * TILE, 3 * TILE, 140, 0x88ff44, 0.8);   // Cauldron
    this.lights.addLight(3.5 * TILE, 3.5 * TILE, 140, 0xffcc44, 0.8); // Counter

    // --- NPCS (Q1.4) ---
    const npcDefs: { x: number; y: number; name: string; role: NPCRole; stationIdx: number | null }[] = [
      { x: 5 * TILE, y: 10 * TILE, name: 'Grom', role: 'blacksmith', stationIdx: 0 },
      { x: 15 * TILE, y: 3 * TILE, name: 'Zara', role: 'alchemist', stationIdx: 1 },
      { x: 5 * TILE, y: 4 * TILE, name: 'Finn', role: 'merchant', stationIdx: 2 },
    ];

    for (const def of npcDefs) {
      const ws = def.stationIdx !== null ? {
        x: stations[def.stationIdx].x,
        y: stations[def.stationIdx].y,
        name: stations[def.stationIdx].name,
      } : null;

      // Role-specific NPC texture
      const texMap: Record<string, string> = {
        blacksmith: 'npc_blacksmith',
        alchemist: 'npc_alchemist',
        merchant: 'npc_merchant',
        guard: 'npc_guard',
      };
      const npcTex = texMap[def.role] || 'npc';

      const npc = new NPCSprite(this, def.x, def.y, def.name, def.role, ws, npcTex);
      this.npcs.push(npc);
      this.npcSprites.push(npc);

      this.physics.add.collider(npc, this.walls);
      this.physics.add.collider(npc, this.doors);
    }

    // --- BT GUARD NPC (Q1.3) ---
    const guard = new BTNPCSprite(this, 19.5 * TILE, 9 * TILE, 'Guard', this.player);
    guard.setTexture('npc_guard');
    guard.setScale(1.3);
    this.npcs.push(guard);
    this.npcSprites.push(guard);
    this.physics.add.collider(guard, this.walls);
    this.physics.add.collider(guard, this.doors);

    // --- LLM NPCs (Phase 2+3 — persistent state) ---
    const allNPCs = [
      { name: 'Grom', role: 'blacksmith', x: 5 * TILE, y: 10 * TILE },
      { name: 'Zara', role: 'alchemist', x: 15 * TILE, y: 3 * TILE },
      { name: 'Finn', role: 'merchant', x: 5 * TILE, y: 4 * TILE },
      { name: 'Guard', role: 'guard', x: 19.5 * TILE, y: 9 * TILE },
    ];

    const defaultLLMs = [
      { id: 'kael', name: 'Kael', role: 'adventurer', x: 10 * TILE, y: 16 * TILE, color: 0x44aaff, objective: 'Find the Crystal of Eternity', inventory: ['Rusty Key'] },
      { id: 'lyra', name: 'Lyra', role: 'scout', x: 3 * TILE, y: 17 * TILE, color: 0x44ff88, objective: 'Map the eastern catacombs', inventory: ['Torch', 'Map Fragment'] },
      { id: 'mordecai', name: 'Mordecai', role: 'sage', x: 20 * TILE, y: 16 * TILE, color: 0xcc88ff, objective: 'Research ancient artifacts in the dungeon', inventory: ['Runic Stone', 'Ancient Scroll'] },
    ];

    // Apply any persisted NPC state over defaults
    const persisted = this._persistedNPCs;
    for (const def of defaultLLMs) {
      const saved = persisted.find(p => p.npc_id === def.id);
      const texKey = `npc_${def.name.toLowerCase()}`;
      const n = new LLMNPCSprite(
        this,
        saved?.pos_x ?? def.x,
        saved?.pos_y ?? def.y,
        def.name,
        this.player,
        texKey,
      );
      n.currentObjective = saved?.objective ?? def.objective;
      n.inventory = saved?.inventory ?? def.inventory;
      n.health = saved?.health ?? 100;
      n.nearbyNPCs = allNPCs.map(p => ({ ...p }));
      this.npcs.push(n);
      this.npcSprites.push(n);
      this.llmNPCs.push(n);
      this.physics.add.collider(n, this.walls);
      this.physics.add.collider(n, this.doors);
    }

    // Load quest progress for each LLM NPC
    this.loadQuestProgress();

    // Set Light2D on all NPCs
    for (const npc of this.npcSprites) {
      npc.setPipeline('Light2D');
    }

    // --- PLAYER ---
    this.player = this.physics.add.sprite(12 * TILE, 10 * TILE, 'player');
    this.player.setCollideWorldBounds(true);
    this.player.setPipeline('Light2D');

    // Player light (follows player)
    this.playerLight = this.lights.addLight(
      this.player.x, this.player.y, 200, 0x8888ff, 1.8
    );

    // Player dust particles
    this.playerDust = this.add.particles(0, 0, 'dust', {
      speed: { min: 5, max: 15 },
      lifespan: 300,
      scale: { start: 1, end: 0 },
      alpha: { start: 0.5, end: 0 },
      frequency: 100,
      emitting: false,
    });
    this.playerDust.setDepth(5);

    // Player collides with walls, doors, and NPCs
    this.physics.add.collider(this.player, this.walls);
    this.physics.add.collider(this.player, this.doors);
    for (const npc of this.npcSprites) {
      this.physics.add.collider(this.player, npc);
    }

    this.physics.world.setBounds(0, 0, MAP_W * TILE, MAP_H * TILE);

    // --- CAMERA ---
    const cam = this.cameras.main;
    cam.setBounds(0, 0, MAP_W * TILE, MAP_H * TILE);
    cam.startFollow(this.player, true, 0.09, 0.09);
    cam.setZoom(1.5);

    // --- MINIMAP (Q4.2) DOM overlay ---
    this.minimapOverlay = new MinimapOverlay();

    // --- HUD (Q4.6) DOM overlay ---
    this.hud = new HUDOverlay();

    // --- INPUT ---
    if (this.input.keyboard) {
      this.cursors = this.input.keyboard.createCursorKeys();
      this.wasd = {
        W: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.W),
        A: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.A),
        S: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.S),
        D: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.D),
      };
    }

    // Audio — init on first user interaction (browser autoplay policy)
    this.audio = new AudioManager();
    const initAudio = () => { this.audio.init(); };
    // Try Phaser keyboard first
    this.input.keyboard?.once('keydown', initAudio);
    // Also listen for click/tap on the canvas
    this.input.once('pointerdown', initAudio);
    // And a global document-level fallback (catches non-Phaser events)
    const docHandler = () => {
      document.removeEventListener('keydown', docHandler);
      document.removeEventListener('click', docHandler);
      initAudio();
    };
    document.addEventListener('keydown', docHandler, { once: true });
    document.addEventListener('click', docHandler, { once: true });

    // H toggle for HUD
    this.input.keyboard?.on('keydown-H', () => this.hud.toggle());
  }

  update(_time: number, delta: number): void {
    // --- PLAYER MOVEMENT ---
    if (!this.player || !this.cursors) return;

    // Don't move when God Console is open
    if (!GodConsole.visible) {
      const speed = 160;
      let vx = 0;
      let vy = 0;

      if (this.cursors.left.isDown || this.wasd.A.isDown) vx = -speed;
      else if (this.cursors.right.isDown || this.wasd.D.isDown) vx = speed;
      if (this.cursors.up.isDown || this.wasd.W.isDown) vy = -speed;
      else if (this.cursors.down.isDown || this.wasd.S.isDown) vy = speed;

      if (vx !== 0 && vy !== 0) {
        vx *= 0.707;
        vy *= 0.707;
      }
      this.player.setVelocity(vx, vy);

      // Update player light position
      this.playerLight.setPosition(this.player.x, this.player.y);

      // Player walk animation (placeholder — needs sprite frames)
      const moving = vx !== 0 || vy !== 0;
      if (moving) {
        // Dust particles
        this.playerDust.emitting = true;
        this.playerDust.setPosition(this.player.x, this.player.y + 10);
        // Footstep sound every ~350ms
        this.stepTimer += delta;
        if (this.stepTimer > 350) {
          this.stepTimer = 0;
          this.audio.playFootstep();
        }
      } else {
        this.playerWalkTimer = 0;
        this.playerDust.emitting = false;
        this.stepTimer = 0;
      }
    } else {
      this.player.setVelocity(0, 0);
      this.player.setScale(1);
      this.playerDust.emitting = false;
    }

    // --- NPC UPDATES (Q1.2 + Q1.5) ---
    for (const npc of this.npcs) {
      npc.update(delta);
    }

    // --- MINIMAP (Q4.2) DOM overlay ---
    const npcPositions = this.npcSprites.map(npc => ({ x: npc.x, y: npc.y }));
    this.minimapOverlay.update(this.player.x, this.player.y, npcPositions);

    // --- HUD (Q4.6) ---
    const nearNPCs = this.npcSprites
      .filter(npc => Phaser.Math.Distance.Between(this.player.x, this.player.y, npc.x, npc.y) < 200)
      .map(npc => ({
        name: (npc as any)._name || npc.texture.key,
        health: (npc as any).health ?? 100,
        objective: (npc as any).currentObjective,
      }));

    // Build quest info for HUD
    const questInfo: { npcName: string; activeQuestTitle: string; questStatus: string }[] = [];
    const llmNames = ['kael', 'lyra', 'mordecai'];
    const nameMap: Record<string, string> = { kael: 'Kael', lyra: 'Lyra', mordecai: 'Mordecai' };
    for (const id of llmNames) {
      const quests = this.npcQuests.get(id) || [];
      const active = quests.find(q => q.status === 'active');
      if (active) {
        questInfo.push({ npcName: nameMap[id] || id, activeQuestTitle: active.title, questStatus: 'active' });
      }
    }

    this.hud.update({
      playerX: this.player.x,
      playerY: this.player.y,
      nearNPCs,
      tasks: [],
      quests: questInfo,
    });

    // Periodic persistence save every 10s
    this.persistTimer += delta;
    if (this.persistTimer > 10000) {
      this.persistTimer = 0;
      const ids = ['kael', 'lyra', 'mordecai'];
      for (let i = 0; i < this.llmNPCs.length; i++) {
        this.saveNPCState(this.llmNPCs[i], ids[i] || 'unknown');
      }
    }
  }

  /** Load NPC positions from persistence API (async). */
  private _persistedNPCs: PersistedNPC[] = [];

  private async loadPersistedState(): Promise<void> {
    try {
      // Load all persisted NPCs
      // We use XMLHttpRequest since Phaser scenes can't easily await in constructor
      const resp = await fetch(`${PERSIST_API}/npcs`);
      const data = await resp.json();
      this._persistedNPCs = data.npcs || [];
      console.log('[Persist] Loaded', this._persistedNPCs.length, 'NPCs from DB');
    } catch (err) {
      console.warn('[Persist] Failed to load NPC state, using defaults:', err);
      this._persistedNPCs = [];
    }
  }

  /** Save an NPC's state to persistence API. */
  private async saveNPCState(npc: LLMNPCSprite, npcId: string): Promise<void> {
    try {
      await fetch(`${PERSIST_API}/npc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          npc_id: npcId,
          npc_name: npc.agentName,
          role: 'adventurer',
          pos_x: Math.round(npc.x),
          pos_y: Math.round(npc.y),
          health: npc.health,
          inventory: npc.inventory,
          status: 'active',
          objective: npc.currentObjective,
        }),
      });
    } catch (err) {
      // Silent — persistence is best-effort
    }
  }

  /** Load quest progress for all LLM NPCs. */
  private async loadQuestProgress(): Promise<void> {
    const npcIds = ['kael', 'lyra', 'mordecai'];
    for (const id of npcIds) {
      try {
        const resp = await fetch(`${PERSIST_API}/quests/progress/${id}`);
        const data = await resp.json();
        if (data.quests) {
          this.npcQuests.set(id, data.quests);
        }
      } catch {
        // Silent
      }
    }
    console.log('[Persist] Loaded quest progress for', npcIds.length, 'NPCs');
  }

  /** Spawn a new LLM NPC dynamically (God Console !spawn). */
  public spawnLLMNPC(
    name: string,
    x: number,
    y: number,
    color: number,
    objective: string = 'Explore the dungeon',
    inventory: string[] = [],
  ): LLMNPCSprite {
    const allNPCs = [
      { name: 'Grom', role: 'blacksmith', x: 5 * 32, y: 10 * 32 },
      { name: 'Zara', role: 'alchemist', x: 15 * 32, y: 3 * 32 },
      { name: 'Finn', role: 'merchant', x: 5 * 32, y: 4 * 32 },
      { name: 'Guard', role: 'guard', x: 19.5 * 32, y: 9 * 32 },
    ];

    const n = new LLMNPCSprite(this, x, y, name, this.player);
    n.setTexture('npc_adventurer');
    n.setTint(color);
    n.currentObjective = objective;
    n.inventory = inventory.length > 0 ? inventory : ['Rusty Key'];
    n.nearbyNPCs = allNPCs.map(p => ({ ...p }));
    this.npcs.push(n);
    this.npcSprites.push(n);
    this.physics.add.collider(n, this.walls);
    this.physics.add.collider(n, this.doors);
    this.physics.add.collider(this.player, n);

    // Spawn sound
    this.audio.playSpawn();

    return n;
  }
}
