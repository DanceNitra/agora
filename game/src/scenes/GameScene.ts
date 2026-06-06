import Phaser from 'phaser';
import { LLMNPCSprite } from '../npc/LLMNPCSprite';
import { VerminSprite } from '../npc/VerminSprite';
import { TILE, MAP_W, MAP_H, DUNGEON_MAP } from '../config/map';
import { GodConsole } from '../GodConsole';
import { MinimapOverlay } from '../MinimapOverlay';
import { AudioManager } from '../audio/AudioManager';
import { HUDOverlay } from '../HUDOverlay';

interface Updatable { update(delta?: number): void; }

interface InteractiveStation { image: Phaser.GameObjects.Image; name: string; x: number; y: number; description: string; }

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
  private playerWalkAnimTime: number = 0;
  private stepTimer: number = 0;
  private playerLight!: Phaser.GameObjects.Light;
  private minimapOverlay!: MinimapOverlay;
  public audio!: AudioManager;
  private hud!: HUDOverlay;
  private persistTimer: number = 0;
  private questRefreshTimer: number = 0;
  private npcQuests: Map<string, PersistedQuest[]> = new Map();
  private interactiveObjects: InteractiveStation[] = [];
  private interactionPrompt!: Phaser.GameObjects.Text;
  private lastInteractionTime: number = 0;
  private interactKey!: Phaser.Input.Keyboard.Key;
  private vermin: VerminSprite[] = [];
  private attackTimer: number = 0;

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

    // --- WORKSTATIONS (Q1.5) — interactive objects ---
    this.interactiveObjects = [];
    const stationDefs = [
      { x: 3.5 * TILE, y: 14 * TILE, texture: 'anvil', name: 'Anvil', desc: 'A heavy anvil. Sparks still glow on its surface.' },
      { x: 20 * TILE, y: 3 * TILE, texture: 'cauldron', name: 'Cauldron', desc: 'A bubbling cauldron filled with luminous green liquid.' },
      { x: 3.5 * TILE, y: 3.5 * TILE, texture: 'counter', name: 'Counter', desc: 'A wooden counter cluttered with curious trinkets.' },
    ];
    for (const s of stationDefs) {
      const img = this.add.image(s.x, s.y, s.texture).setDepth(s.y).setPipeline('Light2D');
      img.setInteractive({ useHandCursor: true });
      img.on('pointerdown', () => this.interactWith(s.name, s.desc));
      this.interactiveObjects.push({ image: img, name: s.name, x: s.x, y: s.y, description: s.desc });
    }
    this.interactionPrompt = this.add.text(0, 0, '', {
      fontSize: '10px', color: '#ffff88',
      backgroundColor: '#000000aa',
      padding: { x: 4, y: 2 },
    }).setOrigin(0.5).setDepth(20).setAlpha(0);

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

    // ═══════════════════════════════════════════
    // NEW ROOMS (Phase A — Dungeon Expansion)
    // ═══════════════════════════════════════════

    // ── LIBRARY (rows 1-5, cols 25-38) ──
    // Bookshelves as decorative elements
    const libraryShelves = [
      { x: 28 * TILE, y: 2 * TILE }, { x: 32 * TILE, y: 2 * TILE }, { x: 36 * TILE, y: 2 * TILE },
      { x: 28 * TILE, y: 4 * TILE }, { x: 32 * TILE, y: 4 * TILE }, { x: 36 * TILE, y: 4 * TILE },
    ];
    for (const s of libraryShelves) {
      this.add.image(s.x, s.y, 'bookshelf').setDepth(s.y).setPipeline('Light2D');
    }
    // Reading table
    this.add.image(30 * TILE, 3 * TILE, 'table').setDepth(3 * TILE + 0.5).setPipeline('Light2D');
    this.add.image(30 * TILE + 8, 3 * TILE - 4, 'bookshelf').setDepth(3 * TILE + 0.4).setScale(0.5);
    // Library light
    this.lights.addLight(30 * TILE, 3 * TILE, 160, 0x8888ff, 1.0);

    // ── TREASURY (rows 7-11, cols 25-32) ──
    // Treasure piles
    this.add.image(27 * TILE, 9 * TILE, 'treasure').setDepth(9 * TILE).setPipeline('Light2D');
    this.add.image(31 * TILE, 10 * TILE, 'treasure').setDepth(10 * TILE).setPipeline('Light2D');
    // Add a chest in treasury
    this.add.image(29 * TILE, 9 * TILE, 'chest').setDepth(9 * TILE).setPipeline('Light2D');
    // Treasury light (golden glow)
    this.lights.addLight(29 * TILE, 9 * TILE, 160, 0xffcc44, 1.3);

    // ── CRYPT (rows 13-17, cols 25-38) ──
    // Tombs
    const tombs = [
      { x: 28 * TILE, y: 14 * TILE }, { x: 28 * TILE, y: 16 * TILE },
      { x: 33 * TILE, y: 15 * TILE }, { x: 33 * TILE, y: 17 * TILE },
      { x: 37 * TILE, y: 14 * TILE }, { x: 37 * TILE, y: 16 * TILE },
    ];
    for (const t of tombs) {
      this.add.image(t.x, t.y, 'tomb').setDepth(t.y).setPipeline('Light2D');
    }
    // Crypt torches (blue/purple flame)
    this.add.image(26 * TILE, 14 * TILE, 'torch').setDepth(14 * TILE).setTint(0x8888ff);
    this.add.image(38 * TILE, 14 * TILE, 'torch').setDepth(14 * TILE).setTint(0x8888ff);
    // Crypt light (dim purple)
    this.lights.addLight(31 * TILE, 15 * TILE, 180, 0x6644aa, 0.7);
    // Torch lights
    for (const t of torches) {
      this.lights.addLight(t.x, t.y, 200, 0xff6622, 1.5);
    }

    // Workstation lights
    this.lights.addLight(3.5 * TILE, 14 * TILE, 140, 0xff8844, 1.0); // Anvil
    this.lights.addLight(20 * TILE, 3 * TILE, 140, 0x88ff44, 0.8);   // Cauldron
    this.lights.addLight(3.5 * TILE, 3.5 * TILE, 140, 0xffcc44, 0.8); // Counter

    // --- NPCS (Q1.4) — all 7 dungeon NPCs as LLM-driven ---
    const stationPositions = [
      { x: 3.5 * TILE, y: 14 * TILE, name: 'Anvil' },
      { x: 20 * TILE, y: 3 * TILE, name: 'Cauldron' },
      { x: 3.5 * TILE, y: 3.5 * TILE, name: 'Counter' },
    ];

    const allNPCs = [
      { name: 'Grom', role: 'blacksmith', x: 5 * TILE, y: 10 * TILE },
      { name: 'Zara', role: 'alchemist', x: 15 * TILE, y: 3 * TILE },
      { name: 'Finn', role: 'merchant', x: 5 * TILE, y: 4 * TILE },
      { name: 'Guard', role: 'guard', x: 19.5 * TILE, y: 9 * TILE },
    ];

    // All 7 LLM NPCs with their roles, objectives, inventories
    const llmDefs = [
      { id: 'kael', name: 'Kael', role: 'adventurer', x: 10 * TILE, y: 16 * TILE, tex: 'npc_kael', color: 0x44aaff, objective: 'Find the Crystal of Eternity', inventory: ['Rusty Key'] },
      { id: 'lyra', name: 'Lyra', role: 'scout', x: 3 * TILE, y: 17 * TILE, tex: 'npc_lyra', color: 0x44ff88, objective: 'Map the eastern catacombs', inventory: ['Torch', 'Map Fragment'] },
      { id: 'mordecai', name: 'Mordecai', role: 'sage', x: 20 * TILE, y: 16 * TILE, tex: 'npc_mordecai', color: 0xcc88ff, objective: 'Research ancient artifacts in the dungeon', inventory: ['Runic Stone', 'Ancient Scroll'] },
      { id: 'grom', name: 'Grom', role: 'blacksmith', x: 5 * TILE, y: 10 * TILE, tex: 'npc_blacksmith', color: 0xff8844, objective: 'Forge weapons for the expedition', inventory: ['Smith Hammer', 'Iron Ore'] },
      { id: 'zara', name: 'Zara', role: 'alchemist', x: 15 * TILE, y: 3 * TILE, tex: 'npc_alchemist', color: 0x44ffaa, objective: 'Brew potions from dungeon herbs', inventory: ['Mortar', 'Herb Pouch'] },
      { id: 'finn', name: 'Finn', role: 'merchant', x: 5 * TILE, y: 4 * TILE, tex: 'npc_merchant', color: 0xffff44, objective: 'Trade supplies with dungeon explorers', inventory: ['Trade Ledger', 'Gold Coins'] },
      { id: 'guard', name: 'Guard', role: 'guard', x: 19.5 * TILE, y: 9 * TILE, tex: 'npc_guard', color: 0x8888cc, objective: 'Patrol the dungeon entrance', inventory: ['Spear', 'Shield'] },
    ];

    // Apply any persisted NPC state over defaults
    const persisted = this._persistedNPCs;
    for (const def of llmDefs) {
      const saved = persisted.find(p => p.npc_id === def.id);
      const n = new LLMNPCSprite(
        this,
        saved?.pos_x ?? def.x,
        saved?.pos_y ?? def.y,
        def.name,
        this.player,
        def.tex,
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

    // ═══════════════════════════════════════════
    // ROAMING VERMIN (Phase A — Combat)
    // ═══════════════════════════════════════════
    const verminSpawns = [
      // Crypt (rows 13-17, cols 25-38)
      { x: 28 * TILE, y: 15 * TILE },
      { x: 32 * TILE, y: 16 * TILE },
      { x: 36 * TILE, y: 14 * TILE },
      { x: 30 * TILE, y: 17 * TILE },
      // Treasury (rows 7-11, cols 25-33)
      { x: 28 * TILE, y: 10 * TILE },
      { x: 32 * TILE, y: 8 * TILE },
      // Library (rows 1-5, cols 25-38)
      { x: 34 * TILE, y: 3 * TILE },
      // Main dungeon corners
      { x: 2 * TILE, y: 5 * TILE },
      { x: 22 * TILE, y: 16 * TILE },
    ];
    for (const s of verminSpawns) {
      const v = new VerminSprite(this, s.x, s.y, this.player);
      this.vermin.push(v);
      this.physics.add.collider(v, this.walls);
      this.physics.add.collider(v, this.doors);
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
      this.interactKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.E);
      this.input.keyboard.on('keydown-E', () => this.checkInteractionProximity());
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

      // Player walk animation — 2-frame wobble + flip
      const moving = vx !== 0 || vy !== 0;
      if (moving) {
        this.playerWalkAnimTime += delta * 0.01;
        const bounce = Math.sin(this.playerWalkAnimTime) * 1.2;
        const squash = Math.abs(Math.sin(this.playerWalkAnimTime * 2)) * 0.03;
        this.player.setY(this.player.y); // keep y stable (walk bounce is visual only via scale)
        this.player.setScale(1 + squash, 1 - squash * 0.5);
        // Flip based on direction
        this.player.setFlipX(vx < 0);
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
        this.playerWalkAnimTime = 0;
        this.player.setScale(1);
        this.player.setFlipX(false);
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

    // --- VERMIN UPDATES + ATTACK ---
    this.attackTimer += delta;
    const spaceDown = this.cursors?.space?.isDown ?? false;
    // Attack on spacebar press (with cooldown)
    if (spaceDown && this.attackTimer > 400) {
      this.attackTimer = 0;
      // Check if any vermin is in attack range
      for (const v of this.vermin) {
        if (!v.alive) continue;
        const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, v.x, v.y);
        if (d < 60) {
          const killed = v.takeDamage(1);
          // Show attack feedback
          const atkText = this.add.text(v.x, v.y - 10, killed ? '💀' : '💥', {
            fontSize: '12px', backgroundColor: '#00000088',
            padding: { x: 2, y: 1 },
          }).setOrigin(0.5).setDepth(20);
          this.tweens.add({
            targets: atkText, alpha: 0, y: atkText.y - 20, duration: 600,
            onComplete: () => atkText.destroy(),
          });
          this.audio.playSparkle();
          // Player knockback
          const kbAngle = Phaser.Math.Angle.Between(v.x, v.y, this.player.x, this.player.y);
          this.player.setVelocity(Math.cos(kbAngle) * 80, Math.sin(kbAngle) * 80);
        }
      }
    }
    // Update all vermin
    for (const v of this.vermin) {
      v.update(delta);
    }

    // --- INTERACTIVE OBJECT PROXIMITY ---
    let nearestObj: InteractiveStation | null = null;
    let nearestDist = 80; // interaction range
    for (const obj of this.interactiveObjects) {
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, obj.x, obj.y);
      if (d < nearestDist) {
        nearestDist = d;
        nearestObj = obj;
      }
    }
    if (nearestObj) {
      this.interactionPrompt.setPosition(nearestObj.x, nearestObj.y - 28);
      this.interactionPrompt.setText(`[E] ${nearestObj.name}`);
      this.interactionPrompt.setAlpha(1);
    } else {
      this.interactionPrompt.setAlpha(0);
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
    const llmNames = ['kael', 'lyra', 'mordecai', 'grom', 'zara', 'finn', 'guard'];
    const nameMap: Record<string, string> = {
      kael: 'Kael', lyra: 'Lyra', mordecai: 'Mordecai',
      grom: 'Grom', zara: 'Zara', finn: 'Finn', guard: 'Guard',
    };
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
      const ids = ['kael', 'lyra', 'mordecai', 'grom', 'zara', 'finn', 'guard'];
      for (let i = 0; i < this.llmNPCs.length; i++) {
        this.saveNPCState(this.llmNPCs[i], ids[i] || 'unknown');
      }
    }

    // Refresh quest progress from DB every 15s (catches auto-started quests)
    this.questRefreshTimer += delta;
    if (this.questRefreshTimer > 15000) {
      this.questRefreshTimer = 0;
      this.loadQuestProgress();
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
    const npcIds = ['kael', 'lyra', 'mordecai', 'grom', 'zara', 'finn', 'guard'];
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

  /** Interact with a workstation object — shows description and fires server event. */
  private interactWith(name: string, description: string): void {
    const now = Date.now();
    if (now - this.lastInteractionTime < 1000) return; // debounce
    this.lastInteractionTime = now;

    // Show interaction text floating above player
    const text = this.add.text(this.player.x, this.player.y - 30, `⚡ ${name}: ${description}`, {
      fontSize: '9px', color: '#ffff88',
      backgroundColor: '#000000aa',
      padding: { x: 3, y: 1 },
      wordWrap: { width: 160 },
    }).setOrigin(0.5).setDepth(20);

    // Fade out after 2.5s
    this.tweens.add({
      targets: text,
      alpha: 0,
      y: text.y - 20,
      duration: 2500,
      onComplete: () => text.destroy(),
    });

    // Fire event to server
    this.audio.playInteract();
    fetch('http://localhost:8000/api/v1/dungeon/interact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_x: Math.round(this.player.x),
        player_y: Math.round(this.player.y),
        object_name: name,
        description,
      }),
    }).catch(() => { /* silent */ });
  }

  /** Called when player presses E near an interactable object. */
  private checkInteractionProximity(): void {
    for (const obj of this.interactiveObjects) {
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, obj.x, obj.y);
      if (d < 80) {
        this.interactWith(obj.name, obj.description);
        return;
      }
    }
  }
}
