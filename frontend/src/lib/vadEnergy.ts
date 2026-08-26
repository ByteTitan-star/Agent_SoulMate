/**
 * Lightweight energy-based VAD helpers (browser AudioWorklet / AnalyserNode).
 * Pure functions so unit tests can cover barge-in state transitions without WebAudio.
 */

export type VadState = 'idle' | 'speech' | 'trailing';

export interface VadConfig {
  /** RMS threshold to enter speech (0..1-ish for normalized PCM). */
  startThreshold: number;
  /** RMS threshold to leave speech. */
  endThreshold: number;
  /** Frames of silence required before emitting speech_end. */
  silenceFrames: number;
  /** Minimum speech frames before a segment is accepted. */
  minSpeechFrames: number;
}

export const DEFAULT_VAD_CONFIG: VadConfig = {
  startThreshold: 0.02,
  endThreshold: 0.012,
  silenceFrames: 10,
  minSpeechFrames: 4,
};

export function rmsFromPcm16(samples: Int16Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i += 1) {
    const v = samples[i]! / 32768;
    sum += v * v;
  }
  return Math.sqrt(sum / samples.length);
}

export function rmsFromFloat32(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i += 1) {
    const v = samples[i]!;
    sum += v * v;
  }
  return Math.sqrt(sum / samples.length);
}

export interface VadTransition {
  next: VadState;
  silenceCount: number;
  speechCount: number;
  event: 'speech_start' | 'speech_end' | null;
}

/**
 * Advance VAD state machine by one energy frame.
 */
export function stepVad(
  state: VadState,
  energy: number,
  silenceCount: number,
  speechCount: number,
  cfg: VadConfig = DEFAULT_VAD_CONFIG
): VadTransition {
  if (state === 'idle') {
    if (energy >= cfg.startThreshold) {
      return { next: 'speech', silenceCount: 0, speechCount: 1, event: 'speech_start' };
    }
    return { next: 'idle', silenceCount: 0, speechCount: 0, event: null };
  }

  if (state === 'speech') {
    if (energy >= cfg.endThreshold) {
      return {
        next: 'speech',
        silenceCount: 0,
        speechCount: speechCount + 1,
        event: null,
      };
    }
    const nextSilence = silenceCount + 1;
    if (nextSilence >= cfg.silenceFrames) {
      const accept = speechCount >= cfg.minSpeechFrames;
      return {
        next: 'idle',
        silenceCount: 0,
        speechCount: 0,
        event: accept ? 'speech_end' : null,
      };
    }
    return {
      next: 'trailing',
      silenceCount: nextSilence,
      speechCount,
      event: null,
    };
  }

  // trailing silence while still inside an utterance
  if (energy >= cfg.endThreshold) {
    return { next: 'speech', silenceCount: 0, speechCount: speechCount + 1, event: null };
  }
  const nextSilence = silenceCount + 1;
  if (nextSilence >= cfg.silenceFrames) {
    const accept = speechCount >= cfg.minSpeechFrames;
    return {
      next: 'idle',
      silenceCount: 0,
      speechCount: 0,
      event: accept ? 'speech_end' : null,
    };
  }
  return { next: 'trailing', silenceCount: nextSilence, speechCount, event: null };
}

export function floatTo16BitPCM(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i += 1) {
    const s = Math.max(-1, Math.min(1, input[i]!));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

export function pcm16ToWavBytes(pcm: Int16Array, sampleRate = 16000): Uint8Array {
  const dataSize = pcm.length * 2;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i += 1) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, dataSize, true);

  const out = new Int16Array(buffer, 44, pcm.length);
  out.set(pcm);
  return new Uint8Array(buffer);
}

export function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}
