import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message } from '@/types';
import { getCsrfToken } from '@/api/client';

const WS_BASE = (import.meta.env.VITE_WS_BASE ?? '').replace(/^http/, 'ws') || `ws://${location.host}`;
const RECONNECT_BASE_MS = 800;
const RECONNECT_MAX_MS = 8000;

export function useChat(characterId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const activeStreamIdRef = useRef<string | null>(null);
  const intentionalCloseRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const characterIdRef = useRef(characterId);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const stopAudioPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  const playBase64Audio = useCallback(
    (b64: string, format: string) => {
      stopAudioPlayback();
      try {
        const mime = format === 'wav' ? 'audio/wav' : 'audio/mpeg';
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
        const url = URL.createObjectURL(new Blob([bytes], { type: mime }));
        audioUrlRef.current = url;
        const audio = new Audio(url);
        audioRef.current = audio;
        void audio.play().catch(() => {
          /* autoplay may be blocked until user gesture */
        });
      } catch {
        // ignore decode/play errors
      }
    },
    [stopAudioPlayback]
  );

  useEffect(() => {
    characterIdRef.current = characterId;
  }, [characterId]);

  useEffect(() => {
    // 切换角色时清空旧消息，避免跨角色串会话
    setMessages([]);
    setInput('');
    setIsStreaming(false);
    activeStreamIdRef.current = null;
  }, [characterId]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current != null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    clearReconnectTimer();
    const ws = wsRef.current;
    if (ws) {
      ws.onopen = null;
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    }
    wsRef.current = null;
    activeStreamIdRef.current = null;
    setIsStreaming(false);
    setConnected(false);
  }, [clearReconnectTimer]);

  const connect = useCallback(() => {
    const current = wsRef.current;
    if (current && (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (current) {
      current.onopen = null;
      current.onclose = null;
      current.onerror = null;
      current.onmessage = null;
      if (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING) {
        current.close();
      }
      wsRef.current = null;
    }

    intentionalCloseRef.current = false;
    const targetId = characterIdRef.current;
    if (!targetId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/chat/${targetId}/`);
    ws.onopen = () => {
      if (characterIdRef.current !== targetId) {
        ws.close();
        return;
      }
      reconnectAttemptRef.current = 0;
      setConnected(true);
    };
    ws.onerror = () => {
      // onclose 会继续处理重连
    };
    ws.onclose = () => {
      if (wsRef.current === ws) wsRef.current = null;
      setConnected(false);
      activeStreamIdRef.current = null;
      setIsStreaming(false);

      if (intentionalCloseRef.current) return;
      if (characterIdRef.current !== targetId) return;

      const attempt = reconnectAttemptRef.current;
      reconnectAttemptRef.current = attempt + 1;
      const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS);
      clearReconnectTimer();
      reconnectTimerRef.current = window.setTimeout(() => {
        if (characterIdRef.current !== targetId || intentionalCloseRef.current) return;
        connect();
      }, delay);
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          setMessages((prev) => [
            ...prev,
            {
              id: data.id || `m-${Date.now()}`,
              role: 'assistant',
              content: data.content || '',
              timestamp: data.timestamp || new Date().toISOString(),
            },
          ]);
        } else if (data.type === 'asr_result') {
          const text = (data.text || '').trim();
          if (!text) return;
          setMessages((prev) => [
            ...prev,
            {
              id: `asr-${Date.now()}`,
              role: 'user',
              content: text,
              timestamp: new Date().toISOString(),
            },
          ]);
        } else if (data.type === 'stream_start') {
          stopAudioPlayback();
          setIsStreaming(true);
          const streamId = data.id || `t-${Date.now()}`;
          activeStreamIdRef.current = streamId;
          setMessages((prev) => [
            ...prev,
            { id: streamId, role: 'assistant', content: '', timestamp: new Date().toISOString() },
          ]);
        } else if (data.type === 'stream_token') {
          setMessages((prev) => {
            const next = [...prev];
            const streamId = data.id || activeStreamIdRef.current;
            const idx = streamId ? next.findIndex((m) => m.id === streamId) : -1;
            if (idx >= 0 && next[idx]?.role === 'assistant') {
              next[idx] = { ...next[idx], content: (next[idx].content || '') + (data.token || '') };
            } else {
              const id = streamId || `t-${Date.now()}`;
              next.push({ id, role: 'assistant', content: data.token || '', timestamp: new Date().toISOString() });
            }
            return next;
          });
        } else if (data.type === 'stream_end' || data.type === 'stream_cancelled') {
          setIsStreaming(false);
          activeStreamIdRef.current = null;
        } else if (data.type === 'interrupted') {
          stopAudioPlayback();
          setIsStreaming(false);
          activeStreamIdRef.current = null;
        } else if (data.type === 'audio' && data.data) {
          playBase64Audio(data.data, data.format || 'mp3');
        } else if (data.type === 'tts_cancelled') {
          stopAudioPlayback();
        } else if (data.type === 'error') {
          setIsStreaming(false);
          activeStreamIdRef.current = null;
        }
      } catch {
        // ignore non-JSON
      }
    };
    wsRef.current = ws;
  }, [clearReconnectTimer, playBase64Audio, stopAudioPlayback]);

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: text.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');

      // Barge-in: allow sending while streaming; backend cancels in-flight reply.
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'message', content: text.trim() }));
        return;
      }

      // 未连接时先尝试重连，并走 REST SSE 兜底
      connect();
      setIsStreaming(true);
      const apiBase = import.meta.env.VITE_API_BASE ?? '/api';
      const csrfToken = getCsrfToken();
      const streamId = `a-${Date.now()}`;
      activeStreamIdRef.current = streamId;

      fetch(`${apiBase}/chat/${characterId}/stream/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({ message: text.trim() }),
      })
        .then((res) => res.body?.getReader())
        .then((reader) => {
          if (!reader) {
            setIsStreaming(false);
            activeStreamIdRef.current = null;
            return;
          }

          setMessages((prev) => [
            ...prev,
            { id: streamId, role: 'assistant', content: '', timestamp: new Date().toISOString() },
          ]);

          const decoder = new TextDecoder();
          let buffer = '';
          const read = () => {
            reader.read().then(({ done, value }) => {
              if (done) {
                setIsStreaming(false);
                activeStreamIdRef.current = null;
                return;
              }
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';
              lines.forEach((line) => {
                if (!line.startsWith('data: ')) return;
                const json = line.slice(6);
                if (json === '[DONE]') return;
                try {
                  const d = JSON.parse(json);
                  const token = d.choices?.[0]?.delta?.content ?? d.text ?? '';
                  if (!token) return;
                  setMessages((prev) => {
                    const next = [...prev];
                    const idx = next.findIndex((m) => m.id === streamId);
                    if (idx >= 0) {
                      next[idx] = { ...next[idx], content: (next[idx].content || '') + token };
                    } else {
                      next.push({ id: streamId, role: 'assistant', content: token, timestamp: new Date().toISOString() });
                    }
                    return next;
                  });
                } catch {
                  // ignore parse error
                }
              });
              read();
            });
          };
          read();
        })
        .catch(() => {
          setIsStreaming(false);
          activeStreamIdRef.current = null;
        });
    },
    [characterId, connect]
  );

  const sendJson = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
    wsRef.current.send(JSON.stringify(payload));
    return true;
  }, []);

  const interrupt = useCallback(() => {
    stopAudioPlayback();
    sendJson({ type: 'interrupt' });
    setIsStreaming(false);
    activeStreamIdRef.current = null;
  }, [sendJson, stopAudioPlayback]);

  const hydrateMessages = useCallback((history: Message[]) => {
    setMessages(history);
  }, []);

  const removeMessageById = useCallback((messageId: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
  }, []);

  return {
    messages,
    input,
    setInput,
    sendMessage,
    sendJson,
    interrupt,
    isStreaming,
    connected,
    connect,
    disconnect,
    hydrateMessages,
    removeMessageById,
  };
}
