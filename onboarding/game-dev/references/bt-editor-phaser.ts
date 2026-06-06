// bt-editor-phaser.ts
// Behavior Tree visual editor + debugger in Phaser 3
// Based on: Colledanchise & Ögren "Behavior Trees in Robotics and AI"

import * as Phaser from 'phaser';

// ============================================================
// 1. BT Runtime with State Caching (for visual debugging)
// ============================================================

export enum NodeState {
    SUCCESS = "SUCCESS",
    FAILURE = "FAILURE",
    RUNNING = "RUNNING",
    IDLE = "IDLE"
}

export abstract class TreeNode {
    public name: string = "Node";
    public lastState: NodeState = NodeState.IDLE;
    abstract tick(): NodeState;
}

export class Action extends TreeNode {
    constructor(name: string, private actionFn: () => NodeState) {
        super();
        this.name = name;
    }
    tick(): NodeState {
        this.lastState = this.actionFn();
        return this.lastState;
    }
}

export class Condition extends TreeNode {
    constructor(name: string, private conditionFn: () => boolean) {
        super();
        this.name = name;
    }
    tick(): NodeState {
        this.lastState = this.conditionFn() ? NodeState.SUCCESS : NodeState.FAILURE;
        return this.lastState;
    }
}

export class Selector extends TreeNode {
    constructor(public children: TreeNode[]) {
        super();
        this.name = "Selector (?)";
    }
    tick(): NodeState {
        for (const child of this.children) {
            const status = child.tick();
            if (status !== NodeState.FAILURE) {
                this.lastState = status;
                return status;
            }
        }
        this.lastState = NodeState.FAILURE;
        return NodeState.FAILURE;
    }
}

export class Sequence extends TreeNode {
    constructor(public children: TreeNode[]) {
        super();
        this.name = "Sequence (->)";
    }
    tick(): NodeState {
        for (const child of this.children) {
            const status = child.tick();
            if (status !== NodeState.SUCCESS) {
                this.lastState = status;
                return status;
            }
        }
        this.lastState = NodeState.SUCCESS;
        return NodeState.SUCCESS;
    }
}

// ============================================================
// 2. JSON Serialization + Factory (data-driven trees)
// ============================================================

export interface BTNodeData {
    type: string;
    name?: string;
    children?: BTNodeData[];
}

export type ActionRegistry = Record<string, () => NodeState>;
export type ConditionRegistry = Record<string, () => boolean>;

export class BTFactory {
    /** Converts JSON blueprint → executable Behavior Tree */
    static deserialize(
        data: BTNodeData,
        actions: ActionRegistry,
        conditions: ConditionRegistry
    ): TreeNode {
        const children = data.children
            ? data.children.map(c => this.deserialize(c, actions, conditions))
            : [];

        switch (data.type) {
            case 'Selector':
                return new Selector(children);
            case 'Sequence':
                return new Sequence(children);
            case 'Action':
                if (!data.name || !actions[data.name]) throw new Error(`Missing Action: ${data.name}`);
                return new Action(data.name, actions[data.name]);
            case 'Condition':
                if (!data.name || !conditions[data.name]) throw new Error(`Missing Cond: ${data.name}`);
                return new Condition(data.name, conditions[data.name]);
            default:
                throw new Error(`Unknown Node Type: ${data.type}`);
        }
    }

    /** Converts instantiated BT back to JSON */
    static serialize(node: TreeNode): BTNodeData {
        let type = 'Unknown';
        if (node instanceof Selector) type = 'Selector';
        else if (node instanceof Sequence) type = 'Sequence';
        else if (node instanceof Action) type = 'Action';
        else if (node instanceof Condition) type = 'Condition';

        const data: BTNodeData = { type, name: node.name };
        if ((node as any).children) {
            data.children = (node as any).children.map((c: TreeNode) => this.serialize(c));
        }
        return data;
    }
}

// ============================================================
// 3. Phaser 3 Visual Debugging Component
// ============================================================

export class BTNodeUI extends Phaser.GameObjects.Container {
    private bg: Phaser.GameObjects.Graphics;
    private label: Phaser.GameObjects.Text;
    private childUIs: BTNodeUI[] = [];

    // Colors mapped to NodeState
    private readonly COLORS = {
        [NodeState.IDLE]: 0x888888,    // Gray — unticked
        [NodeState.RUNNING]: 0xffa500, // Orange — currently executing
        [NodeState.SUCCESS]: 0x00aa00, // Green — passed
        [NodeState.FAILURE]: 0xaa0000  // Red — failed
    };

    constructor(scene: Phaser.Scene, x: number, y: number, public btNode: TreeNode) {
        super(scene, x, y);

        this.bg = scene.add.graphics();
        this.add(this.bg);

        this.label = scene.add.text(0, 0, btNode.name, {
            color: '#ffffff',
            fontSize: '14px',
            backgroundColor: '#000000',
            padding: { x: 5, y: 5 }
        }).setOrigin(0.5, 0.5);
        this.add(this.label);

        this.scene.add.existing(this);
        this.drawBox(NodeState.IDLE);
        this.buildChildrenUI();
    }

    private drawBox(state: NodeState) {
        this.bg.clear();
        this.bg.lineStyle(3, this.COLORS[state], 1);
        this.bg.fillStyle(0x222222, 0.8);

        const width = this.label.width + 20;
        const height = this.label.height + 20;
        this.bg.fillRect(-width / 2, -height / 2, width, height);
        this.bg.strokeRect(-width / 2, -height / 2, width, height);
    }

    private buildChildrenUI() {
        const children = (this.btNode as any).children as TreeNode[];
        if (!children) return;

        const spacingX = 120;
        const startX = -((children.length - 1) * spacingX) / 2;

        children.forEach((childNode, index) => {
            const childX = startX + (index * spacingX);
            const childY = 80;

            // Draw connection line
            const line = this.scene.add.graphics();
            line.lineStyle(2, 0xffffff, 0.5);
            line.beginPath();
            line.moveTo(this.x, this.y + 20);
            line.lineTo(this.x + childX, this.y + childY - 20);
            line.strokePath();

            const childUI = new BTNodeUI(this.scene, this.x + childX, this.y + childY, childNode);
            this.childUIs.push(childUI);
        });
    }

    /** Call in Phaser's update() to refresh colors dynamically */
    public updateVisuals() {
        this.drawBox(this.btNode.lastState);
        this.childUIs.forEach(ui => ui.updateVisuals());
    }
}

// ============================================================
// 4. Example Phaser Scene Integration
// ============================================================

export class EditorScene extends Phaser.Scene {
    private rootUI!: BTNodeUI;
    private rootNode!: TreeNode;

    create() {
        // Define tree in JSON (data-driven)
        const treeData: BTNodeData = {
            type: 'Selector',
            children: [
                {
                    type: 'Sequence',
                    children: [
                        { type: 'Condition', name: 'HasAmmo' },
                        { type: 'Action', name: 'Shoot' }
                    ]
                },
                { type: 'Action', name: 'Reload' }
            ]
        };

        // Define registries
        const conditions = { HasAmmo: () => Math.random() > 0.5 };
        const actions = {
            Shoot: () => NodeState.SUCCESS,
            Reload: () => NodeState.RUNNING
        };

        // Build tree from JSON
        this.rootNode = BTFactory.deserialize(treeData, actions, conditions);
        this.rootUI = new BTNodeUI(this, 400, 100, this.rootNode);
    }

    update() {
        // Tick the tree → updates lastState on all nodes
        this.rootNode.tick();
        // Refresh Phaser visuals
        this.rootUI.updateVisuals();
    }
}
