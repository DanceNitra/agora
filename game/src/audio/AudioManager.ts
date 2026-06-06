/**
 * AudioManager — dungeon ambience + SFX via Web Audio API.
 * No external audio files needed — all sounds are generated procedurally.
 */
export class AudioManager {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private ambienceNode: OscillatorNode | null = null;
  private ambienceGain: GainNode | null = null;
  private muted = false;

  /** Initialise (must be called from user gesture — click/keydown). */
  init(): void {
    if (this.ctx) return;
    console.log('[Audio] init() called — creating AudioContext');
    this.ctx = new AudioContext();
    // Resume if suspended (some browsers keep it suspended even after user gesture)
    if (this.ctx.state === 'suspended') {
      console.log('[Audio] AudioContext is suspended, calling resume()');
      this.ctx.resume();
    }
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0.3;
    this.masterGain.connect(this.ctx.destination);
    console.log('[Audio] AudioContext ready, state:', this.ctx.state);
    this.startAmbience();
  }

  /** Toggle mute on/off. */
  toggleMute(): boolean {
    this.muted = !this.muted;
    if (this.masterGain) {
      this.masterGain.gain.value = this.muted ? 0 : 0.3;
    }
    return this.muted;
  }

  /** Low dungeon drone ambience. */
  private startAmbience(): void {
    if (!this.ctx || !this.masterGain) return;

    // Low rumble
    this.ambienceNode = this.ctx.createOscillator();
    this.ambienceNode.type = 'sawtooth';
    this.ambienceNode.frequency.value = 55;

    // Filter to make it sound distant
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 120;
    filter.Q.value = 1;

    this.ambienceGain = this.ctx.createGain();
    this.ambienceGain.gain.value = 0.06;

    this.ambienceNode.connect(filter);
    filter.connect(this.ambienceGain);
    this.ambienceGain.connect(this.masterGain);
    this.ambienceNode.start();

    // Second layer — wind-like noise
    const bufferSize = this.ctx.sampleRate * 2;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * 0.3;
    }
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;
    noise.loop = true;

    const noiseFilter = this.ctx.createBiquadFilter();
    noiseFilter.type = 'bandpass';
    noiseFilter.frequency.value = 200;
    noiseFilter.Q.value = 0.5;

    const noiseGain = this.ctx.createGain();
    noiseGain.gain.value = 0.03;

    noise.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(this.masterGain);
    noise.start();
  }

  /** Footstep — short low噪 burst. */
  playFootstep(): void {
    if (!this.ctx || !this.masterGain) return;
    const osc = this.ctx.createOscillator();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(80, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(40, this.ctx.currentTime + 0.06);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.08);

    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.08);
  }

  /** Interaction chime — bright short ding. */
  playInteract(): void {
    if (!this.ctx || !this.masterGain) return;
    const osc = this.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1320, this.ctx.currentTime + 0.08);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.15);

    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.15);
  }

  /** Sparkle / magic chime. */
  playSparkle(): void {
    if (!this.ctx || !this.masterGain) return;
    const now = this.ctx.currentTime;
    for (let i = 0; i < 3; i++) {
      const osc = this.ctx.createOscillator();
      osc.type = 'sine';
      const freq = 1200 + i * 400 + Math.random() * 200;
      osc.frequency.setValueAtTime(freq, now + i * 0.05);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.5, now + i * 0.05 + 0.1);

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.08, now + i * 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.05 + 0.12);

      osc.connect(gain);
      gain.connect(this.masterGain);
      osc.start(now + i * 0.05);
      osc.stop(now + i * 0.05 + 0.12);
    }
  }

  /** Spawn whoosh. */
  playSpawn(): void {
    if (!this.ctx || !this.masterGain) return;
    const now = this.ctx.currentTime;

    // Rising tone
    const osc = this.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(200, now);
    osc.frequency.exponentialRampToValueAtTime(800, now + 0.3);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.1, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start(now);
    osc.stop(now + 0.35);
  }

  /** Destroy / cleanup. */
  destroy(): void {
    if (this.ambienceNode) {
      try { this.ambienceNode.stop(); } catch { /* already stopped */ }
    }
    if (this.ctx) {
      this.ctx.close();
    }
    this.ctx = null;
  }
}
