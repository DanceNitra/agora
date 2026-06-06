// dialogue-manager.ts
// Hybrid dialogue system — authored tree + LLM fallback
// Based on: Generative Agents + Behavior Trees condition nodes

export interface PlayerContext {
    inventory: string[];
    questStates: Record<string, string>;
}

export interface DialogueChoice {
    text: string;
    nextId: string; // node ID, "EXIT", or "LLM_FALLBACK"
    condition?: (ctx: PlayerContext) => boolean;
}

export interface DialogueNode {
    id: string;
    speaker: string;
    text: string;
    choices: DialogueChoice[];
}

/**
 * Hybrid Dialogue Manager: authored tree with LLM fallback.
 * Conditions filter choices based on inventory / quest state (like BT condition nodes).
 * "LLM_FALLBACK" delegates to async LLM for open-ended responses.
 */
export class DialogueManager {
    private container!: Phaser.GameObjects.Container;
    private speakerText!: Phaser.GameObjects.Text;
    private dialogueText!: Phaser.GameObjects.Text;
    private choiceTexts: Phaser.GameObjects.Text[] = [];

    private ctx: PlayerContext;
    private db: Map<string, DialogueNode> = new Map();

    constructor(private scene: Phaser.Scene, initialCtx: PlayerContext, x?: number, y?: number) {
        this.ctx = initialCtx;
        this.createUI(x ?? 0, y ?? (scene.scale.height - 200));
    }

    private createUI(x: number, y: number) {
        const w = this.scene.scale.width;
        this.container = this.scene.add.container(x, y).setDepth(1000);

        const bg = this.scene.add.rectangle(w / 2, 100, w - 40, 180, 0x000000, 0.8);
        bg.setStrokeStyle(2, 0xffffff);

        this.speakerText = this.scene.add.text(40, 20, "", { fontSize: '22px', fontStyle: 'bold', color: '#ffcc00' });
        this.dialogueText = this.scene.add.text(40, 50, "", { fontSize: '18px', color: '#ffffff', wordWrap: { width: w - 80 } });

        this.container.add([bg, this.speakerText, this.dialogueText]);
        this.container.setVisible(false);
    }

    loadDialogue(nodes: DialogueNode[]) { nodes.forEach(n => this.db.set(n.id, n)); }
    startDialogue(id: string) { this.container.setVisible(true); this.renderNode(id); }
    closeDialogue() { this.container.setVisible(false); this.clearChoices(); }

    private clearChoices() { this.choiceTexts.forEach(t => t.destroy()); this.choiceTexts = []; }

    private renderNode(id: string) {
        this.clearChoices();
        const node = this.db.get(id);
        if (!node) { this.closeDialogue(); return; }

        this.speakerText.setText(node.speaker);
        this.dialogueText.setText(node.text);

        const valid = node.choices.filter(c => !c.condition || c.condition(this.ctx));
        let y = 110;
        valid.forEach((choice, i) => {
            const t = this.scene.add.text(40, y, `${i + 1}. ${choice.text}`, { fontSize: '16px', color: '#aaaaaa' })
                .setInteractive({ useHandCursor: true })
                .on('pointerover', () => t.setColor('#ffffff'))
                .on('pointerout', () => t.setColor('#aaaaaa'))
                .on('pointerdown', () => this.handleChoice(choice));
            this.container.add(t);
            this.choiceTexts.push(t);
            y += 25;
        });
    }

    private handleChoice(choice: DialogueChoice) {
        if (choice.nextId === "EXIT") this.closeDialogue();
        else if (choice.nextId === "LLM_FALLBACK") this.triggerLLM(choice.text);
        else this.renderNode(choice.nextId);
    }

    private async triggerLLM(playerText: string) {
        this.clearChoices();
        this.speakerText.setText("...");
        this.dialogueText.setText("Thinking...");

        const prompt = `Player has items: [${this.ctx.inventory.join(", ")}]. Quest: ${JSON.stringify(this.ctx.questStates)}. Player says: "${playerText}". Respond in-character, under 2 sentences.`;

        try {
            const response = await this.mockLLMCall(prompt);
            this.speakerText.setText("Guard");
            this.dialogueText.setText(response);

            const exit = this.scene.add.text(40, 110, "1. [Leave]", { fontSize: '16px', color: '#aaaaaa' })
                .setInteractive({ useHandCursor: true })
                .on('pointerdown', () => this.closeDialogue());
            this.container.add(exit);
            this.choiceTexts.push(exit);
        } catch {
            this.dialogueText.setText("I have nothing more to say.");
            setTimeout(() => this.closeDialogue(), 2000);
        }
    }

    private mockLLMCall(prompt: string): Promise<string> {
        return new Promise(resolve => setTimeout(() => {
            resolve(this.ctx.inventory.includes("Rusty Key")
                ? "I see you found the key. Head inside."
                : "Come back when you have the key.");
        }, 1500));
    }
}
