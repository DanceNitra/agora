// minimap-scene.ts
// Mini-map with fog of war and blinking player dot — Phaser 3

export class MinimapScene extends Phaser.Scene {
    private player!: Phaser.Physics.Arcade.Sprite;
    private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
    private minimapCam!: Phaser.Cameras.Scene2D.Camera;
    private playerDot!: Phaser.GameObjects.Arc;
    private fow!: Phaser.GameObjects.RenderTexture;
    private brush!: Phaser.GameObjects.Graphics;

    constructor() { super({ key: 'MinimapScene' }); }

    preload() {
        this.load.image('tiles', 'assets/dungeon_tiles.png');
        this.load.tilemapTiledJSON('map', 'assets/dungeon.json');
        this.load.image('player', 'assets/hero.png');
    }

    create() {
        // 1. World
        const map = this.make.tilemap({ key: 'map' });
        const tileset = map.addTilesetImage('Dungeon', 'tiles');
        if (tileset) {
            map.createLayer('Ground', tileset, 0, 0);
            map.createLayer('Walls', tileset, 0, 0);
        }
        const mw = map.widthInPixels;
        const mh = map.heightInPixels;

        this.player = this.physics.add.sprite(mw / 2, mh / 2, 'player');
        this.cursors = this.input.keyboard!.createCursorKeys();

        // 2. Fog of War — black RenderTexture, erased by player vision
        const visionRadius = 150;
        this.fow = this.add.renderTexture(0, 0, mw, mh).setDepth(50);
        this.fow.fill(0x000000, 0.95);

        this.brush = this.make.graphics({ add: false });
        this.brush.fillStyle(0xffffff, 1);
        this.brush.fillCircle(0, 0, visionRadius);

        // 3. Main camera
        this.cameras.main.setBounds(0, 0, mw, mh);
        this.cameras.main.startFollow(this.player);

        // 4. Minimap camera (top-right corner)
        const miniSize = 200;
        const margin = 10;
        this.minimapCam = this.cameras.add(
            this.scale.width - miniSize - margin, margin, miniSize, miniSize
        );
        this.minimapCam.setZoom(0.15);
        this.minimapCam.setBackgroundColor(0x222222);
        this.minimapCam.startFollow(this.player);
        this.minimapCam.setBounds(0, 0, mw, mh);

        // Border around minimap
        this.add.rectangle(
            this.scale.width - miniSize / 2 - margin,
            miniSize / 2 + margin,
            miniSize, miniSize
        ).setStrokeStyle(4, 0xffffff).setDepth(100).setScrollFactor(0);

        // 5. Player dot (only on minimap, blinks)
        this.playerDot = this.add.circle(this.player.x, this.player.y, 60, 0xff0000).setDepth(60);
        this.cameras.main.ignore(this.playerDot); // Hide from main view

        this.tweens.add({
            targets: this.playerDot, alpha: 0.2,
            yoyo: true, repeat: -1, duration: 400
        });
    }

    update() {
        if (!this.player) return;

        const speed = 300;
        this.player.setVelocity(0);
        if (this.cursors.left.isDown) this.player.setVelocityX(-speed);
        else if (this.cursors.right.isDown) this.player.setVelocityX(speed);
        if (this.cursors.up.isDown) this.player.setVelocityY(-speed);
        else if (this.cursors.down.isDown) this.player.setVelocityY(speed);
        this.player.body?.velocity.normalize().scale(speed);

        // Sync dot
        this.playerDot.x = this.player.x;
        this.playerDot.y = this.player.y;

        // Erase fog of war around player
        this.fow.erase(this.brush, this.player.x, this.player.y);
    }
}
