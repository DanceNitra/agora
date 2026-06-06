import Phaser from 'phaser';

/**
 * BootScene — generates ALL procedural textures.
 * Phase 4: Immersive Polish — detailed pixel-art style textures via code.
 */
export class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: 'BootScene' });
  }

  create(): void {
    this.generateTextures();
    this.scene.start('GameScene');
  }

  private generateTextures(): void {
    const g = (w: number, h: number, draw: (g: Phaser.GameObjects.Graphics) => void) => {
      const gr = this.add.graphics();
      draw(gr);
      return gr;
    };

    const makeTex = (key: string, w: number, h: number, draw: (g: Phaser.GameObjects.Graphics) => void) => {
      const gr = g(w, h, draw);
      gr.generateTexture(key, w, h);
      gr.destroy();
    };

    // ═══════════════════════════════════════════
    // FLOOR — stone slab with mortar and grain
    // ═══════════════════════════════════════════
    makeTex('floor', 32, 32, (g) => {
      // Base stone color
      g.fillStyle(0x2a2a3a, 1);
      g.fillRect(0, 0, 32, 32);

      // Stone texture noise dots
      for (let i = 0; i < 20; i++) {
        const x = Math.random() * 32;
        const y = Math.random() * 32;
        const shade = Math.random() > 0.5 ? 0x33334a : 0x222233;
        g.fillStyle(shade, 0.4);
        g.fillRect(x, y, 3, 3);
      }

      // Mortar lines
      g.lineStyle(1, 0x1a1a2a, 0.7);
      g.lineBetween(0, 8, 32, 8);
      g.lineBetween(0, 16, 32, 16);
      g.lineBetween(0, 24, 32, 24);
      g.lineBetween(8, 0, 8, 8);
      g.lineBetween(24, 0, 24, 8);
      g.lineBetween(16, 8, 16, 16);
      g.lineBetween(8, 16, 8, 24);
      g.lineBetween(24, 16, 24, 24);
      g.lineBetween(16, 24, 16, 32);

      // Subtle highlight top-left
      g.lineStyle(1, 0x44445a, 0.3);
      g.lineBetween(0, 0, 32, 0);
      g.lineBetween(0, 0, 0, 32);

      // Subtle shadow bottom-right
      g.lineStyle(1, 0x111122, 0.3);
      g.lineBetween(0, 31, 32, 31);
      g.lineBetween(31, 0, 31, 32);
    });

    // ── Alternative floor tiles for variation ──
    makeTex('floor2', 32, 32, (g) => {
      g.fillStyle(0x2e2e40, 1);
      g.fillRect(0, 0, 32, 32);

      // Diagonal stone pattern
      g.lineStyle(1, 0x1e1e30, 0.5);
      g.lineBetween(0, 0, 32, 0);
      g.lineBetween(0, 0, 0, 32);
      g.lineBetween(16, 0, 32, 16);
      g.lineBetween(0, 16, 16, 32);

      // Highlight
      g.lineStyle(1, 0x3e3e50, 0.2);
      g.lineBetween(1, 1, 31, 1);
    });

    makeTex('floor3', 32, 32, (g) => {
      g.fillStyle(0x26263a, 1);
      g.fillRect(0, 0, 32, 32);

      // Hexagonal-ish pattern
      g.lineStyle(1, 0x16162a, 0.4);
      g.lineBetween(0, 0, 16, 16);
      g.lineBetween(16, 16, 32, 0);
      g.lineBetween(0, 16, 16, 32);
      g.lineBetween(16, 32, 32, 16);
      g.lineBetween(0, 0, 32, 0);
      g.lineBetween(0, 32, 32, 32);
    });

    // ═══════════════════════════════════════════
    // WALL — brick wall with 3D depth
    // ═══════════════════════════════════════════
    makeTex('wall', 32, 32, (g) => {
      // Dark base
      g.fillStyle(0x3a3a50, 1);
      g.fillRect(0, 0, 32, 32);

      // Brick row 1 (full brick)
      g.fillStyle(0x4a4a66, 1);
      g.fillRect(1, 1, 14, 14);
      g.fillRect(17, 1, 14, 14);

      // Brick row 2 (offset)
      g.fillStyle(0x444460, 1);
      g.fillRect(9, 17, 14, 14);

      // Brick highlights (top edge)
      g.lineStyle(1, 0x5a5a76, 0.5);
      g.lineBetween(1, 1, 15, 1);
      g.lineBetween(17, 1, 31, 1);
      g.lineBetween(9, 17, 23, 17);

      // Brick shadows (bottom edge)
      g.lineStyle(1, 0x2a2a46, 0.5);
      g.lineBetween(1, 15, 15, 15);
      g.lineBetween(17, 15, 31, 15);
      g.lineBetween(9, 31, 23, 31);

      // Mortar lines
      g.lineStyle(1, 0x2a2a40, 0.8);
      g.lineBetween(0, 16, 32, 16);
      g.lineBetween(16, 0, 16, 16);
      g.lineBetween(0, 16, 0, 32);
      g.lineBetween(24, 16, 24, 32);
    });

    // ── Alt wall (darker, damaged) ──
    makeTex('wall2', 32, 32, (g) => {
      g.fillStyle(0x333348, 1);
      g.fillRect(0, 0, 32, 32);

      g.fillStyle(0x434360, 1);
      g.fillRect(1, 1, 14, 14);
      g.fillRect(17, 1, 14, 14);
      g.fillStyle(0x3d3d58, 1);
      g.fillRect(9, 17, 14, 14);

      g.lineStyle(1, 0x232340, 0.8);
      g.lineBetween(0, 16, 32, 16);
      g.lineBetween(16, 0, 16, 16);
      g.lineBetween(0, 16, 0, 32);
      g.lineBetween(24, 16, 24, 32);

      // Crack
      g.lineStyle(1, 0x1a1a30, 0.6);
      g.lineBetween(6, 0, 10, 8);
      g.lineBetween(10, 8, 8, 14);
    });

    // ═══════════════════════════════════════════
    // DOOR — wooden door with iron bands
    // ═══════════════════════════════════════════
    makeTex('door', 32, 32, (g) => {
      // Wood base
      g.fillStyle(0x6b3a2a, 1);
      g.fillRect(0, 0, 32, 32);

      // Wood planks
      g.fillStyle(0x7a4430, 1);
      g.fillRect(2, 1, 12, 30);
      g.fillRect(18, 1, 12, 30);

      // Plank gaps
      g.lineStyle(1, 0x4a2a1a, 0.6);
      g.lineBetween(15, 0, 15, 32);

      // Iron band horizontal
      g.fillStyle(0x555577, 1);
      g.fillRect(0, 6, 32, 4);
      g.fillRect(0, 22, 32, 4);

      // Iron band rivets
      g.fillStyle(0x8888aa, 1);
      g.fillCircle(4, 8, 1.5);
      g.fillCircle(16, 8, 1.5);
      g.fillCircle(28, 8, 1.5);
      g.fillCircle(4, 24, 1.5);
      g.fillCircle(16, 24, 1.5);
      g.fillCircle(28, 24, 1.5);

      // Door handle
      g.fillStyle(0xcccc88, 1);
      g.fillCircle(26, 16, 3);
      g.lineStyle(2, 0xaaaa66, 1);
      g.strokeCircle(26, 16, 3);
    });

    // ═══════════════════════════════════════════
    // PLAYER — armored adventurer
    // ═══════════════════════════════════════════
    makeTex('player', 24, 32, (g) => {
      // Boots
      g.fillStyle(0x553322, 1);
      g.fillRect(5, 26, 6, 6);
      g.fillRect(13, 26, 6, 6);

      // Legs
      g.fillStyle(0x334488, 1);
      g.fillRect(7, 18, 4, 8);
      g.fillRect(13, 18, 4, 8);

      // Body / Armor
      g.fillStyle(0x4466aa, 1);
      g.fillRect(5, 8, 14, 12);

      // Armor chestplate highlight
      g.fillStyle(0x5577bb, 1);
      g.fillRect(7, 10, 10, 6);

      // Belt
      g.fillStyle(0x885522, 1);
      g.fillRect(5, 18, 14, 2);

      // Arms
      g.fillStyle(0x3366aa, 1);
      g.fillRect(1, 10, 5, 10);
      g.fillRect(18, 10, 5, 10);

      // Head
      g.fillStyle(0xddbb99, 1);
      g.fillCircle(12, 5, 6);

      // Hair
      g.fillStyle(0x886644, 1);
      g.fillRect(7, 0, 10, 3);
      g.fillRect(6, 1, 12, 2);

      // Eyes
      g.fillStyle(0x222222, 1);
      g.fillRect(9, 4, 2, 1);
      g.fillRect(14, 4, 2, 1);

      // Helmet outline (blue glow)
      g.lineStyle(1, 0x88bbff, 0.6);
      g.strokeCircle(12, 5, 7);

      // Sword (right side)
      g.fillStyle(0xcccccc, 1);
      g.fillRect(22, 6, 2, 14);
      g.fillStyle(0xaa8844, 1);
      g.fillRect(21, 19, 4, 2);
      g.fillRect(22, 20, 2, 3);
    });

    // ═══════════════════════════════════════════
    // NPC — character sprite (body + head)
    // ═══════════════════════════════════════════
    makeTex('npc', 20, 28, (g) => {
      // Boots
      g.fillStyle(0x443322, 1);
      g.fillRect(4, 22, 5, 6);
      g.fillRect(11, 22, 5, 6);

      // Legs
      g.fillStyle(0x554433, 1);
      g.fillRect(5, 16, 4, 6);
      g.fillRect(11, 16, 4, 6);

      // Body
      g.fillStyle(0x665544, 1);
      g.fillRect(4, 7, 12, 11);

      // Body highlight (chest)
      g.fillStyle(0x887766, 1);
      g.fillRect(6, 9, 8, 5);

      // Arms
      g.fillStyle(0x665544, 1);
      g.fillRect(1, 8, 4, 9);
      g.fillRect(15, 8, 4, 9);

      // Hands
      g.fillStyle(0xddbb99, 1);
      g.fillCircle(3, 17, 2);
      g.fillCircle(17, 17, 2);

      // Head
      g.fillStyle(0xddbb99, 1);
      g.fillCircle(10, 4, 5);

      // Hair
      g.fillStyle(0x664422, 1);
      g.fillRect(6, 0, 8, 2);
      g.fillRect(5, 0, 10, 2);

      // Eyes
      g.fillStyle(0x222222, 1);
      g.fillRect(7, 3, 2, 1);
      g.fillRect(12, 3, 2, 1);
    });

    // ── NPC variants for different roles ──
    const makeNPCVariant = (key: string, bodyColor: number, bodyHighlight: number, hairColor: number) => {
      makeTex(key, 20, 28, (g) => {
        g.fillStyle(0x443322, 1); g.fillRect(4, 22, 5, 6);
        g.fillStyle(0x443322, 1); g.fillRect(11, 22, 5, 6);
        g.fillStyle(0x554433, 1); g.fillRect(5, 16, 4, 6);
        g.fillStyle(0x554433, 1); g.fillRect(11, 16, 4, 6);
        g.fillStyle(bodyColor, 1); g.fillRect(4, 7, 12, 11);
        g.fillStyle(bodyHighlight, 1); g.fillRect(6, 9, 8, 5);
        g.fillStyle(bodyColor, 1); g.fillRect(1, 8, 4, 9);
        g.fillStyle(bodyColor, 1); g.fillRect(15, 8, 4, 9);
        g.fillStyle(0xddbb99, 1); g.fillCircle(3, 17, 2);
        g.fillStyle(0xddbb99, 1); g.fillCircle(17, 17, 2);
        g.fillStyle(0xddbb99, 1); g.fillCircle(10, 4, 5);
        g.fillStyle(hairColor, 1); g.fillRect(6, 0, 8, 2);
        g.fillStyle(hairColor, 1); g.fillRect(5, 0, 10, 2);
        g.fillStyle(0x222222, 1); g.fillRect(7, 3, 2, 1);
        g.fillStyle(0x222222, 1); g.fillRect(12, 3, 2, 1);
      });
    };
    makeNPCVariant('npc_blacksmith', 0x665544, 0x887766, 0x553311);
    makeNPCVariant('npc_alchemist', 0x554466, 0x776688, 0x442244);
    makeNPCVariant('npc_merchant', 0x556644, 0x778866, 0x444422);
    makeNPCVariant('npc_guard', 0x444455, 0x666677, 0x222233);

    // ═══════════════════════════════════════════
    // TORCH — wall torch with flame
    // ═══════════════════════════════════════════
    makeTex('torch', 16, 32, (g) => {
      // Bracket
      g.fillStyle(0x444455, 1);
      g.fillRect(5, 14, 6, 12);

      // Flame outer (orange)
      g.fillStyle(0xff6600, 1);
      g.fillCircle(8, 6, 6);

      // Flame mid (yellow)
      g.fillStyle(0xffaa00, 1);
      g.fillCircle(8, 5, 4);

      // Flame core (white)
      g.fillStyle(0xffeecc, 1);
      g.fillCircle(8, 4, 2);

      // Glow
      g.fillStyle(0xff6600, 0.1);
      g.fillCircle(8, 6, 10);
    });

    // ═══════════════════════════════════════════
    // PILLAR — decorative column
    // ═══════════════════════════════════════════
    makeTex('pillar', 20, 32, (g) => {
      // Base
      g.fillStyle(0x555566, 1);
      g.fillRect(2, 28, 16, 4);

      // Shaft
      g.fillStyle(0x666677, 1);
      g.fillRect(5, 4, 10, 24);

      // Shaft highlight
      g.lineStyle(1, 0x888899, 0.4);
      g.lineBetween(6, 4, 6, 28);

      // Capital
      g.fillStyle(0x555566, 1);
      g.fillRect(0, 0, 20, 4);
      g.fillStyle(0x777788, 1);
      g.fillRect(2, 0, 16, 2);
    });

    // ═══════════════════════════════════════════
    // RUG — decorative floor rug
    // ═══════════════════════════════════════════
    makeTex('rug', 48, 32, (g) => {
      // Rug base
      g.fillStyle(0x882244, 1);
      g.fillRect(0, 4, 48, 24);

      // Border
      g.lineStyle(2, 0xcc6644, 1);
      g.strokeRect(2, 6, 44, 20);

      // Inner pattern
      g.lineStyle(1, 0xaa3355, 0.8);
      g.lineBetween(4, 16, 44, 16);
      g.lineBetween(24, 8, 24, 24);

      // Diamond center
      g.fillStyle(0xcc6644, 0.6);
      g.fillTriangle(24, 10, 18, 16, 30, 16);
      g.fillTriangle(24, 22, 18, 16, 30, 16);

      // Fringe
      g.fillStyle(0x662233, 1);
      g.fillRect(0, 0, 48, 4);
      g.fillRect(0, 28, 48, 4);
    });

    // ═══════════════════════════════════════════
    // CHEST — treasure chest
    // ═══════════════════════════════════════════
    makeTex('chest', 24, 20, (g) => {
      // Box
      g.fillStyle(0x8b5e3c, 1);
      g.fillRect(2, 6, 20, 14);

      // Lid
      g.fillStyle(0x7a4d2b, 1);
      g.fillRect(1, 2, 22, 6);

      // Lid highlight
      g.lineStyle(1, 0xaa7a55, 0.6);
      g.lineBetween(2, 2, 22, 2);

      // Metal bands
      g.fillStyle(0x888899, 1);
      g.fillRect(4, 6, 3, 14);
      g.fillRect(17, 6, 3, 14);

      // Lock
      g.fillStyle(0xffcc44, 1);
      g.fillCircle(12, 12, 3);
      g.fillStyle(0xccaa33, 1);
      g.fillRect(11, 10, 2, 4);

      // Rivets
      g.fillStyle(0xaaaabb, 1);
      g.fillCircle(12, 3, 1.5);
    });

    // ═══════════════════════════════════════════
    // Workstations — enhanced
    // ═══════════════════════════════════════════

    // Anvil (blacksmith)
    makeTex('anvil', 28, 24, (g) => {
      // Base
      g.fillStyle(0x3a3a4a, 1);
      g.fillRect(4, 16, 20, 8);

      // Anvil body
      g.fillStyle(0x555568, 1);
      g.fillRect(6, 8, 16, 8);

      // Anvil top
      g.fillStyle(0x66667a, 1);
      g.fillRect(4, 4, 20, 6);

      // Working surface highlight
      g.fillStyle(0x8888aa, 1);
      g.fillRect(6, 4, 16, 2);

      // Horn (pointy part)
      g.fillStyle(0x555568, 1);
      g.fillTriangle(4, 4, 4, 10, 0, 8);

      // Shadow
      g.lineStyle(1, 0x2a2a3a, 0.5);
      g.lineBetween(4, 16, 24, 16);
    });

    // Cauldron (alchemist)
    makeTex('cauldron', 28, 26, (g) => {
      // Cauldron body
      g.fillStyle(0x3a3a4a, 1);
      g.fillCircle(14, 14, 12);

      // Cauldron rim
      g.fillStyle(0x555568, 1);
      g.fillRect(4, 2, 20, 4);
      g.fillStyle(0x66667a, 1);
      g.fillRect(6, 2, 16, 2);

      // Liquid (glowing green)
      g.fillStyle(0x22aa44, 0.7);
      g.fillCircle(14, 14, 9);

      // Bubble
      g.fillStyle(0x44dd66, 0.5);
      g.fillCircle(12, 12, 3);
      g.fillCircle(17, 15, 2);

      // Legs
      g.fillStyle(0x3a3a4a, 1);
      g.fillRect(4, 22, 4, 4);
      g.fillRect(20, 22, 4, 4);
    });

    // Counter (merchant)
    makeTex('counter', 32, 22, (g) => {
      // Counter top
      g.fillStyle(0x6b4a2a, 1);
      g.fillRect(0, 0, 32, 6);

      // Counter front
      g.fillStyle(0x5a3a1a, 1);
      g.fillRect(0, 6, 32, 16);

      // Wood grain
      g.lineStyle(1, 0x4a2a0a, 0.4);
      g.lineBetween(0, 10, 32, 10);
      g.lineBetween(0, 16, 32, 16);

      // Shelves with items
      g.fillStyle(0x886633, 0.6);
      g.fillRect(2, 8, 8, 6);
      g.fillRect(22, 8, 8, 6);

      // Items on shelves
      g.fillStyle(0x44aa66, 1);
      g.fillCircle(6, 12, 2);
      g.fillStyle(0xaa4444, 1);
      g.fillCircle(26, 12, 2);

      // Top highlight
      g.lineStyle(1, 0x8a6a4a, 0.5);
      g.lineBetween(0, 0, 32, 0);
    });

    // ═══════════════════════════════════════════
    // Environmental particles
    // ═══════════════════════════════════════════

    // Sparkle
    makeTex('sparkle', 8, 8, (g) => {
      g.fillStyle(0xffffff, 1);
      g.fillRect(3, 0, 2, 8);
      g.fillRect(0, 3, 8, 2);
      g.fillRect(2, 2, 4, 4);
    });

    // Dust particle
    makeTex('dust', 4, 4, (g) => {
      g.fillStyle(0xcccccc, 0.6);
      g.fillCircle(2, 2, 2);
    });

    // HP heart
    makeTex('heart', 10, 10, (g) => {
      g.fillStyle(0xff2244, 1);
      g.fillCircle(3, 3, 3);
      g.fillCircle(7, 3, 3);
      g.fillTriangle(1, 4, 9, 4, 5, 9);
    });

    // Empty heart
    makeTex('heart_empty', 10, 10, (g) => {
      g.lineStyle(1, 0x662233, 1);
      g.strokeCircle(3, 3, 3);
      g.strokeCircle(7, 3, 3);
      g.lineBetween(1, 4, 5, 8);
      g.lineBetween(5, 8, 9, 4);
    });

    // ═══════════════════════════════════════════
    // Minimap / Quest markers
    // ═══════════════════════════════════════════

    // Quest marker (exclamation)
    makeTex('marker_quest', 12, 12, (g) => {
      g.fillStyle(0xffcc44, 1);
      g.fillRect(4, 0, 4, 8);
      g.fillRect(3, 8, 6, 2);
      g.fillRect(4, 10, 4, 2);
    });

    // NPC marker (dot)
    makeTex('marker_npc', 6, 6, (g) => {
      g.fillStyle(0x44ff88, 0.8);
      g.fillCircle(3, 3, 3);
    });

    // ═══════════════════════════════════════════
    // LLM NPC — adventurer sprites (colored)
    // ═══════════════════════════════════════════
    const makeLLMNPC = (key: string, armorColor: number, pantsColor: number, hairColor: number) => {
      makeTex(key, 20, 28, (g) => {
        g.fillStyle(0x443322, 1); g.fillRect(4, 22, 5, 6);
        g.fillStyle(0x443322, 1); g.fillRect(11, 22, 5, 6);
        g.fillStyle(pantsColor, 1); g.fillRect(5, 16, 4, 6);
        g.fillStyle(pantsColor, 1); g.fillRect(11, 16, 4, 6);
        g.fillStyle(armorColor, 1); g.fillRect(4, 7, 12, 11);
        // Armor highlight (lighter shade)
        const r = (armorColor >> 16) & 0xff;
        const gr = (armorColor >> 8) & 0xff;
        const b = armorColor & 0xff;
        const lighter = ((Math.min(255, r + 30)) << 16) | ((Math.min(255, gr + 30)) << 8) | (Math.min(255, b + 30));
        g.fillStyle(lighter, 1);
        g.fillRect(6, 9, 8, 5);
        g.fillStyle(armorColor, 1); g.fillRect(1, 8, 4, 9);
        g.fillStyle(armorColor, 1); g.fillRect(15, 8, 4, 9);
        g.fillStyle(0xddbb99, 1); g.fillCircle(3, 17, 2);
        g.fillStyle(0xddbb99, 1); g.fillCircle(17, 17, 2);
        g.fillStyle(0xddbb99, 1); g.fillCircle(10, 4, 5);
        g.fillStyle(hairColor, 1); g.fillRect(6, 0, 8, 2);
        g.fillStyle(hairColor, 1); g.fillRect(5, 0, 10, 2);
        g.fillStyle(0x222222, 1); g.fillRect(7, 3, 2, 1);
        g.fillStyle(0x222222, 1); g.fillRect(12, 3, 2, 1);
        // Cape/accessory
        g.fillStyle(armorColor, 0.3);
        g.fillRect(17, 10, 4, 10);
      });
    };
    makeLLMNPC('npc_kael', 0x3366aa, 0x224488, 0x886644);
    makeLLMNPC('npc_lyra', 0x228844, 0x116633, 0x553311);
    makeLLMNPC('npc_mordecai', 0x7733aa, 0x552288, 0x442244);
    makeLLMNPC('npc_adventurer', 0x666677, 0x444455, 0x553322);

    // ═══════════════════════════════════════════
    // Phase A — New Room Decorations
    // ═══════════════════════════════════════════

    // Bookshelf (library)
    makeTex('bookshelf', 24, 32, (g) => {
      // Frame
      g.fillStyle(0x5a3a1a, 1);
      g.fillRect(0, 0, 24, 32);
      // Shelves
      g.fillStyle(0x7a5a3a, 1);
      g.fillRect(2, 2, 20, 6);
      g.fillRect(2, 12, 20, 6);
      g.fillRect(2, 22, 20, 6);
      // Books
      const bookColors = [0xcc4444, 0x44aa44, 0x4444cc, 0xcccc44, 0xcc44cc, 0x44cccc];
      for (let shelf = 0; shelf < 3; shelf++) {
        const sy = 2 + shelf * 10;
        let bx = 3;
        for (let i = 0; i < 4; i++) {
          const bw = 2 + Math.floor(Math.random() * 3);
          const bh = 5 + Math.floor(Math.random() * 2);
          g.fillStyle(bookColors[(shelf + i) % bookColors.length], 1);
          g.fillRect(bx, sy + (6 - bh), bw, bh);
          bx += bw + 1;
        }
      }
      // Top highlight
      g.lineStyle(1, 0x8a6a4a, 0.5);
      g.lineBetween(0, 0, 24, 0);
    });

    // Table (library reading area)
    makeTex('table', 32, 20, (g) => {
      // Top
      g.fillStyle(0x6b4a2a, 1);
      g.fillRect(0, 0, 32, 4);
      // Legs
      g.fillStyle(0x5a3a1a, 1);
      g.fillRect(2, 4, 3, 16);
      g.fillRect(27, 4, 3, 16);
      // Top highlight
      g.lineStyle(1, 0x8a6a4a, 0.4);
      g.lineBetween(0, 0, 32, 0);
      // Scroll on table
      g.fillStyle(0xddcc88, 1);
      g.fillEllipse(16, 3, 14, 6);
    });

    // Treasure pile (glowing coins)
    makeTex('treasure', 20, 12, (g) => {
      // Base pile
      g.fillStyle(0x886622, 1);
      g.fillCircle(10, 8, 8);
      // Coins
      for (let i = 0; i < 8; i++) {
        const cx = 4 + Math.random() * 12;
        const cy = 3 + Math.random() * 6;
        g.fillStyle(i % 2 === 0 ? 0xffcc44 : 0xccaa33, 1);
        g.fillCircle(cx, cy, 2.5);
      }
      // Glow
      g.fillStyle(0xffdd66, 0.15);
      g.fillCircle(10, 7, 10);
    });

    // Tomb (crypt)
    makeTex('tomb', 24, 20, (g) => {
      // Base
      g.fillStyle(0x444466, 1);
      g.fillRect(2, 8, 20, 12);
      // Lid
      g.fillStyle(0x555577, 1);
      g.fillRect(0, 4, 24, 6);
      // Lid highlight
      g.lineStyle(1, 0x7777aa, 0.4);
      g.lineBetween(1, 4, 23, 4);
      // Engraving
      g.lineStyle(1, 0x333355, 0.6);
      g.lineBetween(4, 12, 20, 12);
      g.lineBetween(4, 16, 20, 16);
      // Skull symbol
      g.fillStyle(0x666688, 1);
      g.fillCircle(12, 14, 3);
      g.fillStyle(0x444466, 1);
      g.fillCircle(11, 13, 1);
      g.fillCircle(13, 13, 1);
      // Cracks
      g.lineStyle(1, 0x333355, 0.3);
      g.lineBetween(6, 4, 10, 8);
    });

    // ═══════════════════════════════════════════
    // Phase A — Roaming Vermin
    // ═══════════════════════════════════════════

    // Vermin (rat/slime/spider)
    makeTex('vermin', 16, 12, (g) => {
      // Body
      g.fillStyle(0x664422, 1);
      g.fillEllipse(8, 7, 12, 8);
      // Head
      g.fillStyle(0x774433, 1);
      g.fillCircle(12, 5, 4);
      // Eyes
      g.fillStyle(0xffff44, 1);
      g.fillCircle(13, 4, 1.5);
      g.fillStyle(0x000000, 1);
      g.fillCircle(13.5, 4, 0.8);
      // Tail
      g.lineStyle(1, 0x553311, 1);
      g.lineBetween(2, 7, 0, 5);
      g.lineBetween(0, 5, -1, 7);
      // Legs
      g.lineStyle(1, 0x553311, 0.6);
      g.lineBetween(5, 10, 3, 12);
      g.lineBetween(8, 10, 6, 12);
      g.lineBetween(11, 10, 9, 12);
    });
  }
}
