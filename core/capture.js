/* ============================================================================
   capture.js — real microphone capture.

   The scorer measures acoustics. Browser voice processing (echo cancellation,
   noise suppression, AGC) rewrites exactly those acoustics, so all three are
   requested OFF. Audio is delivered as 16 kHz mono PCM16 WAV, which is what
   the pipeline expects (librosa.load(..., sr=16000), mono float32).
   ========================================================================== */

export const TARGET_SR = 16000;

export class Recorder {
  constructor() {
    this.stream = null;
    this.ctx = null;
    this.source = null;
    this.node = null;
    this.analyser = null;
    this._chunks = [];
    this._recording = false;
    this.sampleRate = null;
    this.denied = false;
    this.error = null;
  }

  get available() { return !this.denied && !!this.stream; }
  get recording() { return this._recording; }

  /** Ask once. Resolves false if the user declines or there is no mic. */
  async init() {
    if (this.stream) return true;
    if (!navigator.mediaDevices?.getUserMedia) { this.denied = true; this.error = 'no getUserMedia'; return false; }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: false,   // all three off: they distort the
          noiseSuppression: false,   // acoustic detail the scorer reads
          autoGainControl: false,
        },
      });
    } catch (e) {
      this.denied = true; this.error = e?.message || String(e);
      return false;
    }

    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC();
    if (this.ctx.state === 'suspended') await this.ctx.resume();
    this.sampleRate = this.ctx.sampleRate;

    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 256;
    this.source.connect(this.analyser);

    await this._attachTap();
    return true;
  }

  /** AudioWorklet where available, ScriptProcessor as fallback. */
  async _attachTap() {
    const src = `
      class Tap extends AudioWorkletProcessor {
        process(inputs) {
          const ch = inputs[0] && inputs[0][0];
          if (ch && ch.length) this.port.postMessage(ch.slice(0));
          return true;
        }
      }
      registerProcessor('tap', Tap);
    `;
    try {
      const url = URL.createObjectURL(new Blob([src], { type: 'application/javascript' }));
      await this.ctx.audioWorklet.addModule(url);
      URL.revokeObjectURL(url);
      this.node = new AudioWorkletNode(this.ctx, 'tap');
      this.node.port.onmessage = e => { if (this._recording) this._chunks.push(e.data); };
      this.source.connect(this.node);
      // Worklets need a sink to be pulled; a muted gain keeps it silent.
      const mute = this.ctx.createGain();
      mute.gain.value = 0;
      this.node.connect(mute).connect(this.ctx.destination);
      this._tap = 'worklet';
    } catch {
      const sp = this.ctx.createScriptProcessor(4096, 1, 1);
      sp.onaudioprocess = e => {
        if (this._recording) this._chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };
      this.source.connect(sp);
      const mute = this.ctx.createGain();
      mute.gain.value = 0;
      sp.connect(mute).connect(this.ctx.destination);
      this.node = sp;
      this._tap = 'scriptprocessor';
    }
  }

  start() {
    this._chunks = [];
    this._recording = true;
    if (this.ctx?.state === 'suspended') this.ctx.resume();
  }

  /** Stops and returns { blob, durationMs, snrDb, peak } — or null if no audio. */
  stop() {
    this._recording = false;
    if (!this._chunks.length) return null;

    let n = 0;
    for (const c of this._chunks) n += c.length;
    const raw = new Float32Array(n);
    let o = 0;
    for (const c of this._chunks) { raw.set(c, o); o += c.length; }
    this._chunks = [];

    const pcmFull = resampleTo(raw, this.sampleRate, TARGET_SR);
    const pcm = trimSilence(pcmFull, TARGET_SR);
    const blob = encodeWav(pcm, TARGET_SR);
    return {
      blob,
      durationMs: Math.round((pcm.length / TARGET_SR) * 1000),
      snrDb: estimateSnrDb(pcm),
      peak: pcm.reduce((m, v) => Math.max(m, Math.abs(v)), 0),
      sampleRate: TARGET_SR,
    };
  }

  /** 0..1 bar levels for the waveform. */
  levels(n = 22) {
    if (!this.analyser) return null;
    const d = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(d);
    const out = [];
    for (let i = 0; i < n; i++) out.push(d[Math.floor(i * d.length / n)] / 255);
    return out;
  }

  dispose() {
    try { this.stream?.getTracks().forEach(t => t.stop()); } catch {}
    try { this.ctx?.close(); } catch {}
    this.stream = this.ctx = this.source = this.node = this.analyser = null;
  }
}

/* --- trim leading/trailing silence ----------------------------------------
   The recorder always captures a fixed REC_MS window (kid.js), so a quick
   word leaves seconds of trailing room tone in the buffer. Forced alignment
   still has to assign every one of those frames somewhere, and it lands them
   on the last target phone's span — a real "biscuits" take measured a final
   /s/ window of 2160ms where the actual sound was under 100ms. post_max then
   maximises over a window that's almost entirely silence, which is the wrong
   basis for a confidence score. Trimming to the detected speech region (with
   generous padding) keeps every phone's window close to what was actually
   said. */
export function trimSilence(pcm, sampleRate) {
  const frame = Math.floor(sampleRate * 0.02);
  const frameCount = Math.floor(pcm.length / frame);
  if (frameCount < 10) return pcm;                 // too short to bother

  const rms = new Float32Array(frameCount);
  for (let i = 0; i < frameCount; i++) {
    let s = 0;
    const base = i * frame;
    for (let j = base; j < base + frame; j++) s += pcm[j] * pcm[j];
    rms[i] = Math.sqrt(s / frame);
  }
  const sorted = Float32Array.from(rms).sort();
  const noiseFloor = sorted[Math.floor(sorted.length * 0.1)] || 1e-6;
  const peak = sorted[sorted.length - 1] || 1e-6;
  // Conservative on purpose: a real quiet consonant must never be trimmed as
  // "silence", so the bar is well above the measured noise floor.
  const speechThreshold = Math.max(noiseFloor * 3, peak * 0.08);

  let first = -1, last = -1;
  for (let i = 0; i < frameCount; i++) {
    if (rms[i] >= speechThreshold) { if (first === -1) first = i; last = i; }
  }
  if (first === -1) return pcm;   // nothing read as speech; leave it for the SNR gate to reject

  const padFrames = Math.round(0.15 / 0.02);        // 150ms of context on each side
  const startFrame = Math.max(0, first - padFrames);
  const endFrame = Math.min(frameCount - 1, last + padFrames);
  const startSample = startFrame * frame;
  const endSample = Math.min(pcm.length, (endFrame + 1) * frame);
  return pcm.slice(startSample, endSample);
}

/* --- linear resample to 16 kHz ------------------------------------------- */
export function resampleTo(input, fromRate, toRate) {
  if (!fromRate || fromRate === toRate) return input;
  const ratio = fromRate / toRate;
  const out = new Float32Array(Math.round(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const pos = i * ratio;
    const a = Math.floor(pos), b = Math.min(a + 1, input.length - 1);
    const t = pos - a;
    out[i] = input[a] * (1 - t) + input[b] * t;
  }
  return out;
}

/* --- PCM16 WAV, 44-byte canonical header --------------------------------- */
export function encodeWav(samples, sampleRate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const str = (off, s) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)); };

  str(0, 'RIFF');
  v.setUint32(4, 36 + samples.length * 2, true);
  str(8, 'WAVE');
  str(12, 'fmt ');
  v.setUint32(16, 16, true);           // PCM chunk size
  v.setUint16(20, 1, true);            // format = PCM
  v.setUint16(22, 1, true);            // mono
  v.setUint32(24, sampleRate, true);
  v.setUint32(28, sampleRate * 2, true); // byte rate = sr * channels * bytes
  v.setUint16(32, 2, true);            // block align
  v.setUint16(34, 16, true);           // bits per sample
  str(36, 'data');
  v.setUint32(40, samples.length * 2, true);

  let off = 44;
  for (let i = 0; i < samples.length; i++, off += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: 'audio/wav' });
}

/* --- crude SNR estimate --------------------------------------------------
   Quietest decile of 20 ms frames is treated as noise, loudest as signal.
   Only used to pre-empt an obviously unusable take — the server's own
   SNR gate remains authoritative.                                        */
export function estimateSnrDb(pcm, sampleRate = TARGET_SR) {
  const frame = Math.floor(sampleRate * 0.02);
  if (pcm.length < frame * 5) return null;
  const rms = [];
  for (let i = 0; i + frame <= pcm.length; i += frame) {
    let s = 0;
    for (let j = i; j < i + frame; j++) s += pcm[j] * pcm[j];
    rms.push(Math.sqrt(s / frame));
  }
  rms.sort((a, b) => a - b);
  const noise = rms[Math.floor(rms.length * 0.1)] || 1e-8;
  const signal = rms[Math.floor(rms.length * 0.9)] || 1e-8;
  if (signal <= noise) return 0;
  return Math.round(20 * Math.log10(signal / Math.max(noise, 1e-8)) * 10) / 10;
}
