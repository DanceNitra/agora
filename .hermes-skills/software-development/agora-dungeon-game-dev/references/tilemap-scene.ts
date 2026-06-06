// tilemap-scene.ts
// Phaser 3 tile-based dungeon map — Tiled integration
// Based on: Phaser 3 API + Game Programming Patterns

import * as Phaser from 'phaser';

export class TilemapScene extends Phaser.Scene {
    private player!: Phaser.Physics.Arcade.Sprite;
    private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;

    constructor() {
        super({ key: 'TilemapScene' });
    }

    preload(): void {
        // Parallax backgrounds
        this.load.image('bg_sky', 'assets/backgrounds/sky.png');
        this.load.image('bg_mountains', 'assets/backgrounds/mountains.png');

        // Tileset + map
        this.load.image('dungeon_tiles', 'assets/tilesets/dungeon_sheet.png');
        this.load.tilemapTiledJSON('dungeon_map', 'assets/maps/level1.json');

        // Player sprite
        this.load.image('player', 'assets/sprites/hero.png');
    }

    create(): void {
        // --- 1. PARALLAX BACKGROUNDS ---
        const w = this.scale.width;
        const h = this.scale.height;

        this.add.tileSprite(0, 0, w, h, 'bg_sky')
            .setOrigin(0, 0)
            .setScrollFactor(0.1); // Far back — moves slowest

        this.add.tileSprite(0, 0, w, h, 'bg_mountains')
            .setOrigin(0, 0)
            .setScrollFactor(0.4); // Mid-ground

        // --- 2. TILEMAP ---
        const map = this.make.tilemap({ key: 'dungeon_map' });
        const tileset = map.addTilesetImage('DungeonTileset', 'dungeon_tiles');
        if (!tileset) { console.error("Tileset failed to load"); return; }

        const groundLayer = map.createLayer('GroundLayer', tileset, 0, 0);
        const wallLayer = map.createLayer('WallLayer', tileset, 0, 0);
        const waterLayer = map.createLayer('WaterLayer', tileset, 0, 0);

        // --- 3. COLLISIONS (from Tiled custom property 'collides') ---
        if (wallLayer) wallLayer.setCollisionByProperty({ collides: true });
        if (waterLayer) waterLayer.setCollisionByProperty({ collides: true });

        // --- 4. PLAYER ---
        const spawn = map.findObject("Objects", (obj: any) => obj.name === "Spawn Point");
        const sx = spawn ? spawn.x : 100;
        const sy = spawn ? spawn.y : 100;

        this.player = this.physics.add.sprite(sx, sy, 'player');
        this.player.setCollideWorldBounds(true);
        this.physics.world.setBounds(0, 0, map.widthInPixels, map.heightInPixels);

        if (wallLayer) this.physics.add.collider(this.player, wallLayer);
        if (waterLayer) this.physics.add.collider(this.player, waterLayer);

        // --- 5. CAMERA ---
        const cam = this.cameras.main;
        cam.startFollow(this.player, true, 0.05, 0.05);
        cam.setBounds(0, 0, map.widthInPixels, map.heightInPixels);

        if (this.input.keyboard) {
            this.cursors = this.input.keyboard.createCursorKeys();
        }
    }

    update(): void {
        if (!this.player || !this.cursors) return;
        this.player.setVelocity(0);

        const speed = 200;
        if (this.cursors.left.isDown) this.player.setVelocityX(-speed);
        else if (this.cursors.right.isDown) this.player.setVelocityX(speed);
        if (this.cursors.up.isDown) this.player.setVelocityY(-speed);
        else if (this.cursors.down.isDown) this.player.setVelocityY(speed);

        // Normalize diagonal movement
        this.player.body?.velocity.normalize().scale(speed);
    }
}
