// hierarchical-fsm.ts
// Hierarchical Finite State Machine (HFSM) for Agora Dungeon NPC AI
// Based on: Buckland "Programming Game AI by Example"

// ============================================================
// 1. Action
// ============================================================

export class Action {
    constructor(public name: string, private actionFn: () => void) {}
    execute(): void { this.actionFn(); }
}

// ============================================================
// 2. Transition
// ============================================================

export class Transition {
    constructor(
        private condition: () => boolean,
        public targetState: State,
        public transitionAction: Action | null = null
    ) {}

    isTriggered(): boolean { return this.condition(); }
}

// ============================================================
// 3. State (Base)
// ============================================================

export class State {
    public transitions: Transition[] = [];
    public entryActions: Action[] = [];
    public activeActions: Action[] = [];
    public exitActions: Action[] = [];

    constructor(public name: string) {}

    addTransition(transition: Transition) {
        this.transitions.push(transition);
    }

    enter(): void { this.entryActions.forEach(a => a.execute()); }
    execute(): void { this.activeActions.forEach(a => a.execute()); }
    exit(): void { this.exitActions.forEach(a => a.execute()); }
}

// ============================================================
// 4. StateMachine (Composite State — nesting enabled)
// ============================================================

export class StateMachine extends State {
    public currentState: State | null = null;
    public initialState: State | null = null;

    constructor(name: string) {
        super(name);
    }

    setInitialState(state: State) {
        this.initialState = state;
    }

    /**
     * Returns the active state hierarchy for visual debugging.
     * E.g., ["NPC_Brain", "Combat", "Heal"]
     */
    getActiveStates(): string[] {
        const hierarchy = [this.name];
        if (this.currentState) {
            if (this.currentState instanceof StateMachine) {
                hierarchy.push(...this.currentState.getActiveStates());
            } else {
                hierarchy.push(this.currentState.name);
            }
        }
        return hierarchy;
    }

    execute(): void {
        // Run machine-level active actions
        super.execute();

        // Lazy init
        if (!this.currentState) {
            if (this.initialState) {
                this.currentState = this.initialState;
                this.currentState.enter();
            } else {
                return;
            }
        }

        // Priority: check high-level (this machine's) transitions FIRST
        // This ensures interrupt/alarm behaviors work instantly
        let triggered = this.transitions.find(t => t.isTriggered());

        // If no top-level trigger, check current child state's transitions
        if (!triggered && this.currentState) {
            triggered = this.currentState.transitions.find(t => t.isTriggered());
        }

        // Fire transition
        if (triggered) {
            this.currentState.exit();
            if (triggered.transitionAction) {
                triggered.transitionAction.execute();
            }
            this.currentState = triggered.targetState;
            this.currentState.enter();
        }

        // Propagate tick down
        if (this.currentState) {
            this.currentState.execute();
        }
    }
}

// ============================================================
// 5. HFSM Renderer — visual debug in Phaser 3
// ============================================================

export class HFSMDebugRenderer {
    private text: Phaser.GameObjects.Text;

    constructor(scene: Phaser.Scene, x: number, y: number) {
        this.text = scene.add.text(x, y, 'HFSM Debug', {
            fontSize: '14px',
            color: '#00ff00',
            backgroundColor: '#000000aa',
            padding: { x: 8, y: 4 }
        }).setDepth(100);
    }

    /**
     * Call every update() to see live state transitions
     */
    update(machine: StateMachine) {
        const states = machine.getActiveStates();
        const arrows = states.join(' → ');
        const color = states.includes('Combat') ? '#ff4444' :
                      states.includes('Flee') ? '#ffaa00' :
                      states.includes('Alert') ? '#ffff00' : '#00ff00';
        this.text.setStyle({ color, backgroundColor: '#000000aa' });
        this.text.setText(`🧠 ${arrows}`);
    }
}

// ============================================================
// 6. Complete Dungeon NPC Example
// ============================================================

export class DungeonNPC {
    public health: number = 100;
    public hasPotion: boolean = true;
    public seesPlayer: boolean = false;
    public boredom: number = 0;

    public brain: StateMachine = new StateMachine("NPC_Brain");

    constructor() {
        this.setupAI();
    }

    private setupAI() {
        // --- Define hierarchy ---
        const exploreMachine = new StateMachine("Exploration");
        const combatMachine = new StateMachine("Combat");
        const alertState = new State("Alert");
        const fleeState = new State("Flee");

        const idle = new State("Idle");
        const patrol = new State("Patrol");
        const fight = new State("Fight");
        const heal = new State("Heal");

        // --- Actions ---
        idle.activeActions.push(new Action("IdleAnim", () => {
            console.log("NPC is standing around...");
            this.boredom += 1;
        }));

        patrol.activeActions.push(new Action("PatrolAnim", () => {
            console.log("NPC is patrolling the perimeter.");
            this.boredom -= 2;
        }));

        alertState.entryActions.push(new Action("Surprise", () => console.log("NPC: 'Who goes there?!'")));

        fight.activeActions.push(new Action("Attack", () => console.log("NPC is attacking the player!")));

        heal.entryActions.push(new Action("DrinkPotion", () => {
            console.log("NPC is drinking a health potion!");
            this.hasPotion = false;
            this.health = 100;
        }));

        fleeState.activeActions.push(new Action("RunAway", () => console.log("NPC is fleeing in terror!")));

        // --- Wire initial states ---
        this.brain.setInitialState(exploreMachine);
        exploreMachine.setInitialState(idle);
        combatMachine.setInitialState(fight);

        // --- Transitions ---

        // Internal exploration
        idle.addTransition(new Transition(() => this.boredom > 3, patrol));
        patrol.addTransition(new Transition(() => this.boredom <= 0, idle));

        // High-level: explore → alert (interrupt)
        exploreMachine.addTransition(new Transition(() => this.seesPlayer, alertState));

        // Alert → combat or flee
        alertState.addTransition(new Transition(() => this.health >= 40, combatMachine));
        alertState.addTransition(new Transition(() => this.health < 40, fleeState));

        // Combat internal
        fight.addTransition(new Transition(() => this.health < 50 && this.hasPotion, heal));
        heal.addTransition(new Transition(() => this.health >= 100, fight));

        // Combat → flee (interrupt)
        combatMachine.addTransition(new Transition(() => this.health < 20 && !this.hasPotion, fleeState));

        // Flee → explore (when safe)
        fleeState.addTransition(new Transition(() => !this.seesPlayer, exploreMachine));
    }

    public update() {
        this.brain.execute();
    }
}

// ============================================================
// 7. Usage Example
// ============================================================

/*
const npc = new DungeonNPC();

npc.update(); // Idle → boredom++
npc.boredom = 5;
npc.update(); // Patrol

npc.seesPlayer = true;
npc.update(); // Alert → "Who goes there?!"

npc.update(); // Combat → Fight (health >= 40)
npc.health = 30;
npc.update(); // Combat → Heal → heal to 100

npc.seesPlayer = false;
// wait for next tick...
*/
