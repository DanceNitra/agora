// inventory-scene.ts
// Grid-based inventory with drag & drop and equipment slots — Phaser 3

export type ItemCategory = 'weapon' | 'armor' | 'potion' | 'material';

export interface ItemData {
    id: string;
    name: string;
    category: ItemCategory;
    textureKey: string;
}

export class InventoryScene extends Phaser.Scene {
    private readonly COLS = 5;
    private readonly ROWS = 4;
    private readonly SLOT = 64;
    private readonly GAP = 10;
    private readonly SX = 100;
    private readonly SY = 100;

    constructor() { super({ key: 'InventoryScene' }); }

    preload() {
        this.load.image('slot_bg', 'assets/ui/slot.png');
        this.load.image('item_sword', 'assets/items/sword.png');
        this.load.image('item_shield', 'assets/items/shield.png');
        this.load.image('item_potion', 'assets/items/potion.png');
        this.load.image('item_wood', 'assets/items/wood.png');
    }

    create() {
        this.add.text(this.SX, 40, 'Backpack', { fontSize: '24px', color: '#ffffff' });

        // 1. Draw 5×4 inventory grid
        for (let r = 0; r < this.ROWS; r++) {
            for (let c = 0; c < this.COLS; c++) {
                const x = this.SX + c * (this.SLOT + this.GAP);
                const y = this.SY + r * (this.SLOT + this.GAP);
                this.createSlot(x, y, 'any');
            }
        }

        // 2. Equipment slots
        this.add.text(600, 40, 'Equipment', { fontSize: '24px', color: '#ffffff' });

        this.add.text(530, 90, 'Weapon', { fontSize: '14px' });
        this.createSlot(600, 100, 'weapon');

        this.add.text(530, 170, 'Armor', { fontSize: '14px' });
        this.createSlot(600, 180, 'armor');

        this.add.text(530, 250, 'Potion', { fontSize: '14px' });
        this.createSlot(600, 260, 'potion');

        // 3. Mock items
        this.spawnItem({ id: 'w1', name: 'Iron Sword', category: 'weapon', textureKey: 'item_sword' }, 0, 0);
        this.spawnItem({ id: 'a1', name: 'Wooden Shield', category: 'armor', textureKey: 'item_shield' }, 1, 0);
        this.spawnItem({ id: 'p1', name: 'Health Potion', category: 'potion', textureKey: 'item_potion' }, 2, 0);
        this.spawnItem({ id: 'm1', name: 'Oak Wood', category: 'material', textureKey: 'item_wood' }, 3, 0);

        // 4. Drag & drop
        this.setupDragDrop();
    }

    private createSlot(x: number, y: number, category: ItemCategory | 'any') {
        this.add.rectangle(x, y, this.SLOT, this.SLOT, 0x333333).setStrokeStyle(2, 0x888888);
        const zone = this.add.zone(x, y, this.SLOT, this.SLOT).setRectangleDropZone(this.SLOT, this.SLOT);
        zone.setData('accepted', category);
        zone.setData('occupied', null);
    }

    private spawnItem(data: ItemData, col: number, row: number) {
        const x = this.SX + col * (this.SLOT + this.GAP);
        const y = this.SY + row * (this.SLOT + this.GAP);
        const sprite = this.add.sprite(x, y, data.textureKey);
        sprite.setDisplaySize(this.SLOT - 10, this.SLOT - 10);
        sprite.setData('itemData', data);
        sprite.setInteractive({ draggable: true, useHandCursor: true });
    }

    private setupDragDrop() {
        this.input.on('dragstart', (ptr: any, obj: Phaser.GameObjects.Sprite) => {
            this.children.bringToTop(obj);
            obj.setScale(1.1);
            obj.setData('startX', obj.x);
            obj.setData('startY', obj.y);
        });

        this.input.on('drag', (ptr: any, obj: Phaser.GameObjects.Sprite, dx: number, dy: number) => {
            obj.x = dx;
            obj.y = dy;
        });

        this.input.on('drop', (ptr: any, obj: Phaser.GameObjects.Sprite, zone: Phaser.GameObjects.Zone) => {
            const item: ItemData = obj.getData('itemData');
            const accepted = zone.getData('accepted');
            if (accepted === 'any' || accepted === item.category) {
                obj.x = zone.x;
                obj.y = zone.y;
                zone.setData('occupied', obj);
            } else {
                this.revert(obj);
            }
        });

        this.input.on('dragend', (ptr: any, obj: Phaser.GameObjects.Sprite, dropped: boolean) => {
            obj.setScale(1.0);
            if (!dropped) this.revert(obj);
        });
    }

    private revert(obj: Phaser.GameObjects.Sprite) {
        obj.x = obj.getData('startX');
        obj.y = obj.getData('startY');
    }
}
