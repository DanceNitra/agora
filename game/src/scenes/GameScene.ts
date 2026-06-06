import Phaser from 'phaser';
import { NPCSprite, NPCRole } from '../npc/NPCSprite';
import { BTNPCSprite } from '../npc/BTNPCSprite';
import { LLMNPCSprite } from '../npc/LLMNPCSprite';
import { TILE, MAP_W, MAP_H, DUNGEON_MAP } from '../config/map';
import { GodConsole } from '../GodConsole';

interface Updatable { update(delta?: number): void; }

export class GameScene extends Phaser.Scene {
  private player!: Phaser.Physics.Arcade.Sprite;
  private walls!: Phaser.Physics.Arcade.StaticGroup;
  private doors!: Phaser.Physics.Arcade.StaticGroup;
  private npcs: Updatable[] = [];
  private npcSprites: Phaser.Physics.Arcade.Sprite[] = [];
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: Record<string, Phaser.Input.Keyboard.Key>;

  constructor() {
    super({ key: 'GameScene' });
  }

  create(): void {
    // --- TILEMAP ---
    this.walls = this.physics.add.staticGroup();
    this.doors = this.physics.add.staticGroup();

    for (let y = 0; y < MAP_H; y++) {
      for (let x = 0; x < MAP_W; x++) {
        const tile = DUNGEON_MAP[y][x];
        const px = x * TILE + TILE / 2;
        const py = y * TILE + TILE / 2;

        if (tile === 0) {
          this.add.image(px, py, 'floor');
        } else if (tile === 1) {
          const w = this.walls.create(px, py, 'wall') as Phaser.Physics.Arcade.Sprite;
          w.refreshBody();
        } else if (tile === 2) {
          const d = this.doors.create(px, py, 'door') as Phaser.Physics.Arcade.Sprite;
          d.refreshBody();
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
      this.add.image(s.x, s.y, s.texture).setDepth(s.y);
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
      this.add.image(t.x, t.y, 'torch').setDepth(t.y);
    }

    // Pillars
    const pillars = [
      { x: 8 * TILE, y: 7 * TILE },
      { x: 16 * TILE, y: 7 * TILE },
      { x: 8 * TILE, y: 13 * TILE },
      { x: 16 * TILE, y: 13 * TILE },
    ];
    for (const p of pillars) {
      this.add.image(p.x, p.y, 'pillar').setDepth(p.y);
    }

    // Rug in center
    this.add.image(12 * TILE, 10 * TILE, 'rug').setDepth(10 * TILE + 0.5);

    // Chest
    this.add.image(1.5 * TILE, 17 * TILE, 'chest').setDepth(17 * TILE);

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

    // --- LLM NPCs (Phase 2+3 — multiple agents) ---
    const allNPCs = [
      { name: 'Grom', role: 'blacksmith', x: 5 * TILE, y: 10 * TILE },
      { name: 'Zara', role: 'alchemist', x: 15 * TILE, y: 3 * TILE },
      { name: 'Finn', role: 'merchant', x: 5 * TILE, y: 4 * TILE },
      { name: 'Guard', role: 'guard', x: 19.5 * TILE, y: 9 * TILE },
    ];

    const llmNPCs = [
      {
        name: 'Kael', x: 10 * TILE, y: 16 * TILE, color: 0x44aaff,
        objective: 'Find the Crystal of Eternity',
        inventory: ['Rusty Key'],
      },
      {
        name: 'Lyra', x: 3 * TILE, y: 17 * TILE, color: 0x44ff88,
        objective: 'Map the eastern catacombs',
        inventory: ['Torch', 'Map Fragment'],
      },
      {
        name: 'Mordecai', x: 20 * TILE, y: 16 * TILE, color: 0xcc88ff,
        objective: 'Research ancient artifacts in the dungeon',
        inventory: ['Runic Stone', 'Ancient Scroll'],
      },
    ];

    for (const lnpc of llmNPCs) {
      const texKey = `npc_${lnpc.name.toLowerCase()}`;
      const n = new LLMNPCSprite(this, lnpc.x, lnpc.y, lnpc.name, this.player, texKey);
      n.currentObjective = lnpc.objective;
      n.inventory = lnpc.inventory;
      n.nearbyNPCs = allNPCs.map(p => ({ ...p }));
      this.npcs.push(n);
      this.npcSprites.push(n);
      this.physics.add.collider(n, this.walls);
      this.physics.add.collider(n, this.doors);
    }

    // --- PLAYER ---
    this.player = this.physics.add.sprite(12 * TILE, 10 * TILE, 'player');
    this.player.setCollideWorldBounds(true);

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
    } else {
      this.player.setVelocity(0, 0);
    }

    // --- NPC UPDATES (Q1.2 + Q1.5) ---
    for (const npc of this.npcs) {
      npc.update(delta);
    }
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

    return n;
  }
}
