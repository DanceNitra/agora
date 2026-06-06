// steering-behaviors-phaser.ts
// Full steering behaviors for Phaser 3 — Agora Dungeon NPC movement
// Based on: Millington & Funge "Artificial Intelligence for Games"

import Phaser from 'phaser';

// ============================================================
// 1. Steering Agent — the Vehicle
// ============================================================

export class SteeringAgent extends Phaser.GameObjects.Sprite {
    public mass: number = 1.0;
    public maxSpeed: number = 150;
    public maxForce: number = 5;

    public velocity: Phaser.Math.Vector2;
    public steeringForce: Phaser.Math.Vector2;

    // Wander properties
    public wanderAngle: number = 0;
    public wanderDistance: number = 50;
    public wanderRadius: number = 30;
    public wanderJitter: number = 0.5;

    // Path following
    private path: Phaser.Math.Vector2[] = [];
    private currentWaypointIndex: number = 0;
    private waypointSeekDist: number = 20;

    constructor(scene: Phaser.Scene, x: number, y: number, texture: string) {
        super(scene, x, y, texture);
        scene.add.existing(this);
        this.velocity = new Phaser.Math.Vector2(0, 0);
        this.steeringForce = new Phaser.Math.Vector2(0, 0);
    }

    // ============================================================
    // 2. Physics Update Loop
    // ============================================================

    update(time: number, delta: number) {
        this.steeringForce = this.calculateBlendedSteering();
        this.steeringForce.limit(this.maxForce);
        const acceleration = this.steeringForce.clone().scale(1 / this.mass);
        this.velocity.add(acceleration);
        this.velocity.limit(this.maxSpeed);
        const deltaSec = delta / 1000;
        this.x += this.velocity.x * deltaSec;
        this.y += this.velocity.y * deltaSec;
        if (this.velocity.lengthSq() > 0.00001) {
            this.rotation = this.velocity.angle();
        }
    }

    // ============================================================
    // 3. Core Steering Behaviors
    // ============================================================

    seek(targetPos: Phaser.Math.Vector2): Phaser.Math.Vector2 {
        const pos = new Phaser.Math.Vector2(this.x, this.y);
        const desired = targetPos.clone().subtract(pos);
        desired.normalize().scale(this.maxSpeed);
        return desired.subtract(this.velocity);
    }

    flee(targetPos: Phaser.Math.Vector2): Phaser.Math.Vector2 {
        const pos = new Phaser.Math.Vector2(this.x, this.y);
        const desired = pos.subtract(targetPos);
        desired.normalize().scale(this.maxSpeed);
        return desired.subtract(this.velocity);
    }

    arrive(targetPos: Phaser.Math.Vector2, arrivalRadius: number = 100): Phaser.Math.Vector2 {
        const pos = new Phaser.Math.Vector2(this.x, this.y);
        const toTarget = targetPos.clone().subtract(pos);
        const distance = toTarget.length();
        if (distance > arrivalRadius) return this.seek(targetPos);
        if (distance > 0) {
            const speed = (distance / arrivalRadius) * this.maxSpeed;
            const desired = toTarget.clone().normalize().scale(speed);
            return desired.subtract(this.velocity);
        }
        return new Phaser.Math.Vector2(0, 0);
    }

    pursuit(evader: SteeringAgent): Phaser.Math.Vector2 {
        const toEvader = new Phaser.Math.Vector2(evader.x - this.x, evader.y - this.y);
        const maxSpeed = Math.max(this.maxSpeed, evader.velocity.length());
        const lookAhead = toEvader.length() / (maxSpeed + 0.001);
        const predicted = new Phaser.Math.Vector2(evader.x, evader.y)
            .add(evader.velocity.clone().scale(lookAhead));
        return this.seek(predicted);
    }

    evasion(pursuer: SteeringAgent): Phaser.Math.Vector2 {
        const toPursuer = new Phaser.Math.Vector2(pursuer.x - this.x, pursuer.y - this.y);
        const maxSpeed = Math.max(this.maxSpeed, pursuer.velocity.length());
        const lookAhead = toPursuer.length() / (maxSpeed + 0.001);
        const predicted = new Phaser.Math.Vector2(pursuer.x, pursuer.y)
            .add(pursuer.velocity.clone().scale(lookAhead));
        return this.flee(predicted);
    }

    wander(): Phaser.Math.Vector2 {
        this.wanderAngle += (Math.random() * 2 - 1) * this.wanderJitter;
        const circleCenter = this.velocity.clone().normalize().scale(this.wanderDistance);
        const displacement = new Phaser.Math.Vector2(
            Math.cos(this.wanderAngle) * this.wanderRadius,
            Math.sin(this.wanderAngle) * this.wanderRadius
        );
        return circleCenter.add(displacement);
    }

    obstacleAvoidance(obstacles: { x: number; y: number; radius: number }[]): Phaser.Math.Vector2 {
        const detectionLength = 40 + (this.velocity.length() / this.maxSpeed) * 40;
        const ahead = new Phaser.Math.Vector2(this.x, this.y)
            .add(this.velocity.clone().normalize().scale(detectionLength));
        let closest = null;
        let closestDist = Infinity;
        for (const obs of obstacles) {
            const dist = Phaser.Math.Distance.Between(ahead.x, ahead.y, obs.x, obs.y);
            if (dist < obs.radius && dist < closestDist) { closest = obs; closestDist = dist; }
        }
        if (closest) {
            return ahead.clone().subtract(new Phaser.Math.Vector2(closest.x, closest.y)).normalize().scale(this.maxSpeed);
        }
        return new Phaser.Math.Vector2(0, 0);
    }

    // ============================================================
    // 4. Blended Steering
    // ============================================================

    calculateBlendedSteering(): Phaser.Math.Vector2 {
        const total = new Phaser.Math.Vector2(0, 0);
        // Override in subclass with weighted behaviors
        return total;
    }

    // ============================================================
    // 5. Path Following (A* integration)
    // ============================================================

    setPath(waypoints: { x: number; y: number }[]): void {
        this.path = waypoints.map(w => new Phaser.Math.Vector2(w.x, w.y));
        this.currentWaypointIndex = 0;
    }

    followPath(): Phaser.Math.Vector2 {
        if (!this.path || this.currentWaypointIndex >= this.path.length) {
            return new Phaser.Math.Vector2(0, 0);
        }
        const waypoint = this.path[this.currentWaypointIndex];
        const pos = new Phaser.Math.Vector2(this.x, this.y);
        const dist = pos.distance(waypoint);
        if (dist < this.waypointSeekDist) {
            this.currentWaypointIndex++;
            return this.followPath();
        }
        if (this.currentWaypointIndex === this.path.length - 1) {
            return this.arrive(waypoint);
        }
        return this.seek(waypoint);
    }

    get isPathComplete(): boolean {
        return !this.path || this.currentWaypointIndex >= this.path.length;
    }
}

// ============================================================
// 6. Flocking
// ============================================================

export class FlockingSystem {
    constructor(
        private seperationWeight: number = 2.0,
        private alignmentWeight: number = 1.0,
        private cohesionWeight: number = 1.0,
        private neighborRadius: number = 60
    ) {}

    separation(agent: SteeringAgent, neighbors: SteeringAgent[]): Phaser.Math.Vector2 {
        const force = new Phaser.Math.Vector2(0, 0);
        for (const other of neighbors) {
            const dist = Phaser.Math.Distance.Between(agent.x, agent.y, other.x, other.y);
            if (dist > 0 && dist < this.neighborRadius) {
                const away = new Phaser.Math.Vector2(agent.x - other.x, agent.y - other.y);
                away.scale(1 / dist);
                force.add(away);
            }
        }
        return force;
    }

    alignment(agent: SteeringAgent, neighbors: SteeringAgent[]): Phaser.Math.Vector2 {
        if (neighbors.length === 0) return new Phaser.Math.Vector2(0, 0);
        const avgVelocity = new Phaser.Math.Vector2(0, 0);
        for (const other of neighbors) avgVelocity.add(other.velocity);
        avgVelocity.scale(1 / neighbors.length);
        return avgVelocity.subtract(agent.velocity).scale(this.alignmentWeight);
    }

    cohesion(agent: SteeringAgent, neighbors: SteeringAgent[]): Phaser.Math.Vector2 {
        if (neighbors.length === 0) return new Phaser.Math.Vector2(0, 0);
        const center = new Phaser.Math.Vector2(0, 0);
        for (const other of neighbors) { center.x += other.x; center.y += other.y; }
        center.scale(1 / neighbors.length);
        return agent.seek(center);
    }

    calculate(agent: SteeringAgent, neighbors: SteeringAgent[]): Phaser.Math.Vector2 {
        const total = new Phaser.Math.Vector2(0, 0);
        total.add(this.separation(agent, neighbors).scale(this.seperationWeight));
        total.add(this.alignment(agent, neighbors).scale(this.alignmentWeight));
        total.add(this.cohesion(agent, neighbors).scale(this.cohesionWeight));
        return total;
    }
}

// ============================================================
// 7. Patrol NPC Example
// ============================================================

export class PatrolAgent extends SteeringAgent {
    private patrolPoints: Phaser.Math.Vector2[];
    private currentPatrolIndex: number = 0;

    constructor(scene: Phaser.Scene, x: number, y: number, texture: string, patrolPath: { x: number; y: number }[]) {
        super(scene, x, y, texture);
        this.patrolPoints = patrolPath.map(p => new Phaser.Math.Vector2(p.x, p.y));
        this.maxSpeed = 80;
        this.wanderJitter = 1.0;
    }

    calculateBlendedSteering(): Phaser.Math.Vector2 {
        const total = new Phaser.Math.Vector2(0, 0);
        total.add(this.wander().scale(0.5));
        if (this.patrolPoints.length > 0) {
            const target = this.patrolPoints[this.currentPatrolIndex];
            const pos = new Phaser.Math.Vector2(this.x, this.y);
            const dist = pos.distance(target);
            if (dist < 20) {
                this.currentPatrolIndex = (this.currentPatrolIndex + 1) % this.patrolPoints.length;
            }
            if (this.currentPatrolIndex === 0 && dist < 20) {
                total.add(this.arrive(target).scale(1.5));
            } else {
                total.add(this.seek(target).scale(1.5));
            }
        }
        return total;
    }
}
