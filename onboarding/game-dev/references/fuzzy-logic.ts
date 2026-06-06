// fuzzy-logic.ts
// Fuzzy Logic system for Game AI — Agora Dungeon NPC decision making
// Based on: Buckland "Programming Game AI by Example"

// ============================================================
// 1. Membership Functions
// ============================================================

abstract class FuzzySet {
    public DOM: number = 0; // Degree of Membership (holds rule-inferred confidence)
    abstract calculateDOM(val: number): number;
}

/** Triangular: min → peak → max. DOM ramps up to peak, then down. */
class TriangleSet extends FuzzySet {
    constructor(public min: number, public peak: number, public max: number) { super(); }

    calculateDOM(val: number): number {
        if (val <= this.min || val >= this.max) return 0.0;
        if (val === this.peak) return 1.0;
        if (val < this.peak) return (val - this.min) / (this.peak - this.min);
        return (this.max - val) / (this.max - this.peak);
    }
}

/** Left Shoulder (Trapezoidal): DOM = 1 up to peakEnd, then ramps down. */
class LeftShoulderSet extends FuzzySet {
    constructor(public peakEnd: number, public max: number) { super(); }

    calculateDOM(val: number): number {
        if (val <= this.peakEnd) return 1.0;
        if (val >= this.max) return 0.0;
        return (this.max - val) / (this.max - this.peakEnd);
    }
}

/** Right Shoulder (Trapezoidal): RAMPS up from min, DOM = 1 at peakStart onward. */
class RightShoulderSet extends FuzzySet {
    constructor(public min: number, public peakStart: number) { super(); }

    calculateDOM(val: number): number {
        if (val <= this.min) return 0.0;
        if (val >= this.peakStart) return 1.0;
        return (val - this.min) / (this.peakStart - this.min);
    }
}

// ============================================================
// 2. Fuzzy Linguistic Variable (FLV)
// ============================================================

class FuzzyVariable {
    public sets: Record<string, FuzzySet> = {};

    addSet(name: string, set: FuzzySet): FuzzySet {
        this.sets[name] = set;
        return set;
    }

    /** Fuzzification: map crisp value → DOM for each set */
    fuzzify(val: number): void {
        for (const key in this.sets) {
            this.sets[key].DOM = this.sets[key].calculateDOM(val);
        }
    }
}

// ============================================================
// 3. Fuzzy Rules & Inference
// ============================================================

class FuzzyRule {
    constructor(public antecedents: FuzzySet[], public consequent: FuzzySet) {}

    /** Inference: AND = min(DOMs). If multiple rules fire same consequent, OR = max(DOM). */
    calculate(): void {
        const confidence = Math.min(...this.antecedents.map(a => a.DOM));
        this.consequent.DOM = Math.max(this.consequent.DOM, confidence);
    }
}

// ============================================================
// 4. Fuzzy Module & Defuzzification (COG)
// ============================================================

class FuzzyModule {
    public variables: Record<string, FuzzyVariable> = {};
    public rules: FuzzyRule[] = [];

    createFLV(name: string): FuzzyVariable {
        const flv = new FuzzyVariable();
        this.variables[name] = flv;
        return flv;
    }

    addRule(antecedents: FuzzySet[], consequent: FuzzySet): void {
        this.rules.push(new FuzzyRule(antecedents, consequent));
    }

    /** Center of Gravity (Centroid) defuzzification */
    defuzzifyCOG(flvName: string, minRange: number, maxRange: number, samples: number = 15): number {
        const outputFLV = this.variables[flvName];
        let totalWeight = 0.0;
        let totalMoment = 0.0;
        const stepSize = (maxRange - minRange) / samples;

        for (let s = 1; s <= samples; s++) {
            const value = minRange + (s * stepSize);
            let maxDOM = 0.0;

            for (const key in outputFLV.sets) {
                const set = outputFLV.sets[key];
                const capped = Math.min(set.calculateDOM(value), set.DOM);
                maxDOM = Math.max(maxDOM, capped);
            }

            totalMoment += value * maxDOM;
            totalWeight += maxDOM;
        }

        return totalWeight === 0.0 ? 0.0 : totalMoment / totalWeight;
    }

    /** Full pipeline: Fuzzify → Infer → Defuzzify */
    evaluate(inputs: Record<string, number>, outputFLV: string, outMin: number, outMax: number): number {
        // Clear previous consequent DOMs
        for (const key in this.variables[outputFLV].sets) {
            this.variables[outputFLV].sets[key].DOM = 0.0;
        }

        // Step 1: Fuzzify inputs
        for (const key in inputs) {
            this.variables[key].fuzzify(inputs[key]);
        }

        // Step 2: Run rules
        this.rules.forEach(rule => rule.calculate());

        // Step 3: Defuzzify
        return this.defuzzifyCOG(outputFLV, outMin, outMax);
    }
}

// ============================================================
// 5. Example: Enemy Threat Assessment
// ============================================================

export function threatAssessmentExample(health: number, distance: number): number {
    const fm = new FuzzyModule();

    // --- Health (0-100) ---
    const h = fm.createFLV("Health");
    const hLow = h.addSet("Low", new LeftShoulderSet(25, 50));
    const hMed = h.addSet("Medium", new TriangleSet(25, 50, 75));
    const hHigh = h.addSet("High", new RightShoulderSet(50, 75));

    // --- Distance (0-50 meters) ---
    const d = fm.createFLV("Distance");
    const dClose = d.addSet("Close", new LeftShoulderSet(10, 25));
    const dMed = d.addSet("Medium", new TriangleSet(10, 25, 40));
    const dFar = d.addSet("Far", new RightShoulderSet(25, 40));

    // --- Threat output (0-100) ---
    const t = fm.createFLV("Threat");
    const tLow = t.addSet("Low", new LeftShoulderSet(30, 50));
    const tMed = t.addSet("Medium", new TriangleSet(30, 50, 70));
    const tHigh = t.addSet("High", new RightShoulderSet(50, 70));

    // --- Rules ---
    fm.addRule([hLow, dClose], tHigh);      // Low HP + close enemy = HIGH threat
    fm.addRule([hMed, dMed], tMed);          // Medium HP + medium distance = MEDIUM
    fm.addRule([hHigh, dFar], tLow);         // High HP + far enemy = LOW
    fm.addRule([hLow, dFar], tMed);          // Low HP but far = MEDIUM

    return fm.evaluate({ Health: health, Distance: distance }, "Threat", 0, 100);
}

// Test: 35 HP + 15m away → fuzzy threat level
// console.log(threatAssessmentExample(35, 15));
