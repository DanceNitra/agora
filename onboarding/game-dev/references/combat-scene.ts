// combat-scene.ts
// Turn-based combat system for Agora Dungeon — Phaser 3
// FSM states: INIT → PLAYER_SELECT → ACTION_EXECUTING → ENEMY_TURN → GAME_OVER

import * as Phaser from 'phaser';

// ============================================================
// 1. Fighter — encapsulates logic + UI (HP bar, statuses)
// ============================================================

export class Fighter {
    public hpBarBg!: Phaser.GameObjects.Rectangle;
    public hpBarFill!: Phaser.GameObjects.Rectangle;
    public statusText!: Phaser.GameObjects.Text;

    constructor(
        public scene: Phaser.Scene,
        public name: string,
        public isPlayer: boolean,
        public hp: number,
        public maxHp: number,
        public sprite: Phaser.GameObjects.Sprite,
        public startX: number,
        public startY: number,
        public statuses: string[] = []
    ) {
        this.createUI();
    }

    private createUI() {
        const yOff = this.isPlayer ? 60 : -60;
        this.hpBarBg = this.scene.add.rectangle(this.startX, this.startY + yOff, 100, 10, 0x000000).setOrigin(0.5);
        this.hpBarFill = this.scene.add.rectangle(this.startX - 50, this.startY + yOff, 100, 10, 0x00ff00).setOrigin(0, 0.5);
        this.statusText = this.scene.add.text(this.startX, this.startY + yOff + 15, '', { fontSize: '12px', color: '#ffff00' }).setOrigin(0.5);
        this.updateUI();
    }

    public takeDamage(amount: number) {
        this.hp = Math.max(0, this.hp - amount);
        this.updateUI();
        this.sprite.setTint(0xff0000);
        this.scene.time.delayedCall(200, () => this.sprite.clearTint());
    }

    public addStatus(status: string) {
        this.statuses.push(status);
        this.updateUI();
    }

    private updateUI() {
        const pct = this.hp / this.maxHp;
        this.hpBarFill.width = 100 * pct;
        this.hpBarFill.fillColor = pct > 0.3 ? 0x00ff00 : 0xff0000;
        this.statusText.setText(this.statuses.join(', '));
    }
}

// ============================================================
// 2. Combat Scene with FSM
// ============================================================

enum BattleState {
    INIT,
    PLAYER_SELECT,
    ACTION_EXECUTING,
    ENEMY_TURN,
    GAME_OVER
}

export class CombatScene extends Phaser.Scene {
    private state: BattleState = BattleState.INIT;
    private player!: Fighter;
    private enemy!: Fighter;
    private logText!: Phaser.GameObjects.Text;
    private actionLog: string[] = [];
    private attackBtn!: Phaser.GameObjects.Text;
    private poisonBtn!: Phaser.GameObjects.Text;

    constructor() {
        super({ key: 'CombatScene' });
    }

    preload() {
        this.load.image('hero', 'assets/hero.png');
        this.load.image('monster', 'assets/monster.png');
    }

    create() {
        const heroSprite = this.add.sprite(200, 300, 'hero');
        const monsterSprite = this.add.sprite(600, 300, 'monster');

        this.player = new Fighter(this, "Kael", true, 100, 100, heroSprite, 200, 300);
        this.enemy = new Fighter(this, "Slime", false, 80, 80, monsterSprite, 600, 300);

        // Action log UI
        this.add.rectangle(400, 500, 700, 150, 0x222222, 0.8).setOrigin(0.5);
        this.logText = this.add.text(100, 440, '', { fontSize: '16px', color: '#ffffff', wordWrap: { width: 600 } });

        // Combat buttons
        this.attackBtn = this.add.text(100, 100, '> Attack', { fontSize: '24px', color: '#ffffff' })
            .setInteractive({ useHandCursor: true })
            .on('pointerdown', () => this.executeAction(this.player, this.enemy, "Attack"));

        this.poisonBtn = this.add.text(100, 140, '> Poison', { fontSize: '24px', color: '#ffffff' })
            .setInteractive({ useHandCursor: true })
            .on('pointerdown', () => this.executeAction(this.player, this.enemy, "Poison"));

        this.log("A wild Slime appears!");
        this.changeState(BattleState.PLAYER_SELECT);
    }

    // ============================================================
    // FSM
    // ============================================================

    private changeState(next: BattleState) {
        this.state = next;
        switch (this.state) {
            case BattleState.PLAYER_SELECT:
                this.attackBtn.setAlpha(1);
                this.poisonBtn.setAlpha(1);
                break;
            case BattleState.ACTION_EXECUTING:
                this.attackBtn.setAlpha(0.3);
                this.poisonBtn.setAlpha(0.3);
                break;
            case BattleState.ENEMY_TURN:
                this.log(`${this.enemy.name} is thinking...`);
                this.time.delayedCall(1000, () => this.executeAction(this.enemy, this.player, "Attack"));
                break;
            case BattleState.GAME_OVER:
                this.attackBtn.destroy();
                this.poisonBtn.destroy();
                this.add.text(400, 150, 'BATTLE OVER', { fontSize: '48px', color: '#ff0000' }).setOrigin(0.5);
                break;
        }
    }

    private log(msg: string) {
        this.actionLog.push(msg);
        if (this.actionLog.length > 5) this.actionLog.shift();
        this.logText.setText(this.actionLog.join('\n'));
    }

    // ============================================================
    // Action execution (tween → damage → death check → next state)
    // ============================================================

    private executeAction(attacker: Fighter, defender: Fighter, action: string) {
        if (this.state !== BattleState.PLAYER_SELECT && attacker.isPlayer) return;
        this.changeState(BattleState.ACTION_EXECUTING);

        const forwardX = attacker.isPlayer ? attacker.startX + 50 : attacker.startX - 50;

        this.tweens.add({
            targets: attacker.sprite,
            x: forwardX,
            duration: 200,
            yoyo: true,
            onYoyo: () => {
                if (action === "Attack") {
                    const dmg = Phaser.Math.Between(10, 20);
                    defender.takeDamage(dmg);
                    this.log(`${attacker.name} attacks ${defender.name} for ${dmg} damage!`);
                } else if (action === "Poison") {
                    defender.addStatus("POISON");
                    this.log(`${attacker.name} poisoned ${defender.name}!`);
                }
            },
            onComplete: () => {
                if (defender.hp <= 0) {
                    this.log(`${defender.name} has been defeated!`);
                    this.changeState(BattleState.GAME_OVER);
                } else if (attacker.isPlayer) {
                    this.changeState(BattleState.ENEMY_TURN);
                } else {
                    this.processStatusEffects(this.player);
                    if (this.player.hp > 0) this.changeState(BattleState.PLAYER_SELECT);
                }
            }
        });
    }

    private processStatusEffects(fighter: Fighter) {
        if (fighter.statuses.includes("POISON")) {
            const dmg = 5;
            fighter.takeDamage(dmg);
            this.log(`${fighter.name} takes ${dmg} poison damage.`);
            if (fighter.hp <= 0) {
                this.log(`${fighter.name} succumbed to poison!`);
                this.changeState(BattleState.GAME_OVER);
            }
        }
    }
}
