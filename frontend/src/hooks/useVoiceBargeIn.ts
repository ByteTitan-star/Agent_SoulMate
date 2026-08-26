import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DEFAULT_VAD_CONFIG,
  bytesToBase64,
  floatTo16BitPCM,
  pcm16ToWavBytes,
  rmsFromFloat32,
  stepVad,
  type VadState,
} from '@/lib/vadEnergy';

type SendJson = (payload: Record<string, unknown>) => boolean;

/**
 * Browser mic capture + energy VAD that drives backend barge-in protocol.
 */
export function useVoiceBargeIn(sendJson: SendJson, enabled: boolean) {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const stateRef = useRef<VadState>('idle');
  const silenceRef = useRef(0);
  const speechRef = useRef(0);
  const chunkBufferRef = useRef<Int16Array[]>([]);

  const stop = useCallback(() => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    void audioCtxRef.current?.close();
    audioCtxRef.current = null;
    stateRef.current = 'idle';
    silenceRef.current = 0;
    speechRef.current = 0;
    chunkBufferRef.current = [];
    setListening(false);
    setSpeaking(false);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
      });
      streamRef.current = stream;
      const ctx = new AudioContext({ sampleRate: 16000 });
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;
      // ScriptProcessor is deprecated but widely available without worklet bundling.
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (ev) => {
        const input = ev.inputBuffer.getChannelData(0);
        const energy = rmsFromFloat32(input);
        const transition = stepVad(
          stateRef.current,
          energy,
          silenceRef.current,
          speechRef.current,
          DEFAULT_VAD_CONFIG
        );
        stateRef.current = transition.next;
        silenceRef.current = transition.silenceCount;
        speechRef.current = transition.speechCount;

        if (transition.event === 'speech_start') {
          setSpeaking(true);
          chunkBufferRef.current = [];
          sendJson({ type: 'vad_start' });
        }

        if (transition.next === 'speech' || transition.next === 'trailing') {
          chunkBufferRef.current.push(floatTo16BitPCM(input));
        }

        if (transition.event === 'speech_end') {
          if (chunkBufferRef.current.length) {
            const merged = mergePcm(chunkBufferRef.current);
            chunkBufferRef.current = [];
            const sampleRate = audioCtxRef.current?.sampleRate ?? 16000;
            const wav = pcm16ToWavBytes(merged, sampleRate);
            sendJson({ type: 'audio_chunk', data: bytesToBase64(wav) });
          }
          setSpeaking(false);
          sendJson({ type: 'vad_end' });
        }
      };

      const silentGain = ctx.createGain();
      silentGain.gain.value = 0;
      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(ctx.destination);
      setListening(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法访问麦克风');
      stop();
    }
  }, [sendJson, stop]);

  useEffect(() => {
    if (enabled) {
      void start();
    } else {
      stop();
    }
    return () => stop();
  }, [enabled, start, stop]);

  return { listening, speaking, error, start, stop };
}

function mergePcm(chunks: Int16Array[]): Int16Array {
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const out = new Int16Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  return out;
}
