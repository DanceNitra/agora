// behavior-tree-runtime.ts
// Full Behavior Tree implementation for Agora Dungeon NPC AI
// Based on: Colledanchise & Ögren "Behavior Trees in Robotics and AI" (arXiv:1709.00084)

// --- 1. Node Execution States ---
export enum NodeState {
    SUCCESS = "SUCCESS",
    FAILURE = "FAILURE",
    RUNNING = "RUNNING"
}

// --- 2. Base Node ---
export abstract class TreeNode {
    abstract tick(): NodeState;
}

// --- 3. Execution Nodes ---

/**
 * Action: Executes a command.
 * Returns SUCCESS if completed, FAILURE if impossible, or RUNNING while ongoing.
 */
export class Action extends TreeNode {
    constructor(
        private name: string,
        private actionFn: () => NodeState
    ) {
        super();
    }

    tick(): NodeState {
        console.log(`[Action] Executing: ${this.name}`);
        return this.actionFn();
    }
}

/**
 * Condition: Checks a proposition.
 * Returns SUCCESS or FAILURE depending on if the proposition holds. Never returns RUNNING.
 */
export class Condition extends TreeNode {
    constructor(
        private name: string,
        private conditionFn: () => boolean
    ) {
        super();
    }

    tick(): NodeState {
        const result = this.conditionFn();
        console.log(`[Condition] Checking: ${this.name} -> ${result}`);
        return result ? NodeState.SUCCESS : NodeState.FAILURE;
    }
}

// --- 4. Control Flow Nodes ---

/**
 * Sequence: Routes ticks to its children from the left.
 * Returns FAILURE or RUNNING if any child returns such. Returns SUCCESS only if all succeed.
 * On RUNNING: halts execution and returns RUNNING immediately — does NOT continue to next child.
 */
export class Sequence extends TreeNode {
    constructor(private children: TreeNode[]) {
        super();
    }

    tick(): NodeState {
        for (const child of this.children) {
            const childStatus = child.tick();
            if (childStatus === NodeState.RUNNING) {
                return NodeState.RUNNING;
            } else if (childStatus === NodeState.FAILURE) {
                return NodeState.FAILURE;
            }
        }
        return NodeState.SUCCESS;
    }
}

/**
 * Selector (Fallback): Routes ticks to its children from the left.
 * Returns SUCCESS or RUNNING if any child returns such. Returns FAILURE only if all fail.
 * On RUNNING: halts execution and returns RUNNING immediately.
 */
export class Selector extends TreeNode {
    constructor(private children: TreeNode[]) {
        super();
    }

    tick(): NodeState {
        for (const child of this.children) {
            const childStatus = child.tick();
            if (childStatus === NodeState.RUNNING) {
                return NodeState.RUNNING;
            } else if (childStatus === NodeState.SUCCESS) {
                return NodeState.SUCCESS;
            }
        }
        return NodeState.FAILURE;
    }
}

/**
 * Parallel: Routes ticks to all children simultaneously.
 * Returns SUCCESS if M children succeed, FAILURE if N - M + 1 children fail, else RUNNING.
 */
export class Parallel extends TreeNode {
    constructor(
        private children: TreeNode[],
        private successThreshold: number // M — how many need to succeed
    ) {
        super();
    }

    tick(): NodeState {
        let successCount = 0;
        let failureCount = 0;

        for (const child of this.children) {
            const childStatus = child.tick();
            if (childStatus === NodeState.SUCCESS) successCount++;
            if (childStatus === NodeState.FAILURE) failureCount++;
        }

        if (successCount >= this.successThreshold) {
            return NodeState.SUCCESS;
        } else if (failureCount > this.children.length - this.successThreshold) {
            return NodeState.FAILURE;
        }
        return NodeState.RUNNING;
    }
}

/**
 * Decorator: Has a single child and manipulates its return status.
 * Example: Inverter — inverts SUCCESS <-> FAILURE, RUNNING passes through.
 */
export class Inverter extends TreeNode {
    constructor(private child: TreeNode) {
        super();
    }

    tick(): NodeState {
        const childStatus = this.child.tick();
        if (childStatus === NodeState.SUCCESS) return NodeState.FAILURE;
        if (childStatus === NodeState.FAILURE) return NodeState.SUCCESS;
        return NodeState.RUNNING; // Running status is NOT inverted
    }
}

/**
 * Repeat: Repeats the child N times or forever. Returns SUCCESS when done.
 */
export class Repeat extends TreeNode {
    private counter: number = 0;

    constructor(
        private child: TreeNode,
        private times: number = -1 // -1 = infinite
    ) {
        super();
    }

    tick(): NodeState {
        if (this.times >= 0 && this.counter >= this.times) {
            return NodeState.SUCCESS;
        }
        const result = this.child.tick();
        if (result !== NodeState.RUNNING) {
            this.counter++;
        }
        return NodeState.RUNNING;
    }

    reset(): void {
        this.counter = 0;
    }
}

// --- 5. Memory-efficient BT — the Running Node Pattern ---
// For BT persistence across ticks: store which node was RUNNING last tick
// and resume from there instead of checking all children again.

export interface BTState {
    runningNodeIndex: number; // -1 = none
    runningNodeType: 'selector' | 'sequence' | null;
}

// --- 6. Example: Dungeon Guard NPC Behavior Tree ---
// Patrol → Detect player → Combat → Flee when low health → Heal → Patrol

export function createGuardBehaviorTree(guard: any): TreeNode {
    return new Selector([
        // Priority 1: Flee if low health
        new Sequence([
            new Condition("Low Health?", () => guard.health < 20),
            new Action("Flee to safe room", () => {
                guard.flee();
                return guard.isFleeing ? NodeState.RUNNING : NodeState.SUCCESS;
            })
        ]),
        // Priority 2: Combat if player detected
        new Sequence([
            new Condition("Player Detected?", () => guard.canSeePlayer),
            new Action("Attack Player", () => {
                guard.attack();
                return guard.isAttacking ? NodeState.RUNNING : NodeState.SUCCESS;
            })
        ]),
        // Priority 3: Patrol
        new Sequence([
            new Action("Patrol route", () => {
                guard.patrol();
                return guard.isPatrolling ? NodeState.RUNNING : NodeState.SUCCESS;
            })
        ])
    ]);
}

// --- 7. Example: Door Open / Enter Room ---
// "If door is open, enter. Otherwise, open door then enter."

let isDoorOpen = false;
let isMoving = false;

const doorOpenCondition = new Condition("Is Door Open?", () => isDoorOpen);

const openDoorAction = new Action("Open Door", () => {
    isDoorOpen = true;
    return NodeState.SUCCESS;
});

const enterRoomAction = new Action("Move into Room", () => {
    if (!isMoving) {
        isMoving = true;
        return NodeState.RUNNING; // Ongoing action
    }
    return NodeState.SUCCESS; // Completed on next tick
});

const exampleTree = new Selector([
    new Sequence([doorOpenCondition, enterRoomAction]),
    new Sequence([openDoorAction, enterRoomAction])
]);

// Tick execution:
// Tick 1: Door closed → Condition fails → Selector tries second Sequence → Open Door → Enter RUNNING → Tree RUNNING
// Tick 2: Door open → First Sequence starts → Condition succeeds → Enter SUCCESS → Tree SUCCESS

// --- 8. BT JSON Serialization (for editor/debug) ---
export function treeToJson(node: TreeNode): any {
    if (node instanceof Action) {
        return { type: "action", name: (node as any).name };
    }
    if (node instanceof Condition) {
        return { type: "condition", name: (node as any).name };
    }
    if (node instanceof Sequence) {
        return { type: "sequence", children: (node as any).children.map(treeToJson) };
    }
    if (node instanceof Selector) {
        return { type: "selector", children: (node as any).children.map(treeToJson) };
    }
    if (node instanceof Parallel) {
        return {
            type: "parallel",
            successThreshold: (node as any).successThreshold,
            children: (node as any).children.map(treeToJson)
        };
    }
    if (node instanceof Inverter) {
        return { type: "inverter", child: treeToJson((node as any).child) };
    }
    return { type: "unknown" };
}
