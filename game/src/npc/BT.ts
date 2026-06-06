/**
 * Behavior Tree runtime — adapted for Phaser NPC AI.
 * Nodes: Action, Condition, Sequence, Selector, Inverter
 * Based on: Colledanchise & Ögren (arXiv:1709.00084)
 */

export enum BTState {
  SUCCESS = "SUCCESS",
  FAILURE = "FAILURE",
  RUNNING = "RUNNING",
}

export abstract class BTNode {
  abstract tick(): BTState;
}

// --- Leaf Nodes ---

export class BTAction extends BTNode {
  constructor(public name: string, private fn: () => BTState) {
    super();
  }
  tick(): BTState {
    return this.fn();
  }
}

export class BTCondition extends BTNode {
  constructor(public name: string, private fn: () => boolean) {
    super();
  }
  tick(): BTState {
    return this.fn() ? BTState.SUCCESS : BTState.FAILURE;
  }
}

// --- Control Flow ---

/** All children must succeed. Returns RUNNING/FAILURE immediately. */
export class BTSequence extends BTNode {
  constructor(private children: BTNode[]) {
    super();
  }
  tick(): BTState {
    for (const child of this.children) {
      const s = child.tick();
      if (s !== BTState.SUCCESS) return s;
    }
    return BTState.SUCCESS;
  }
}

/** First child to succeed → whole tree succeeds. */
export class BTSelector extends BTNode {
  constructor(private children: BTNode[]) {
    super();
  }
  tick(): BTState {
    for (const child of this.children) {
      const s = child.tick();
      if (s !== BTState.FAILURE) return s;
    }
    return BTState.FAILURE;
  }
}

/** Inverts SUCCESS ↔ FAILURE. RUNNING passes through. */
export class BTInverter extends BTNode {
  constructor(private child: BTNode) {
    super();
  }
  tick(): BTState {
    const s = this.child.tick();
    if (s === BTState.RUNNING) return BTState.RUNNING;
    return s === BTState.SUCCESS ? BTState.FAILURE : BTState.SUCCESS;
  }
}
