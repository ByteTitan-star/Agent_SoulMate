import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message } from '@/types';
import { getCsrfToken } from '@/api/client';

const WS_BASE = (import.meta.env.VITE_WS_BASE ?? '').replace(/^http/, 'ws') || `ws://${location.host}`;

export function useChat(characterId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const activeStreamIdRef = useRef<string | null>(null);

  useEffect(() => {
    // 切换角色时清空旧消息，避免跨角色串会话
    setMessages([]);
    setInput('');
    setIsStreaming(false);
    activeStreamIdRef.current = null;
  }, [characterId]);

  const disconnect = useCallback(() => {
    const ws = wsRef.current;
    if (ws) {
      ws.onopen = null;
      ws.onclose = null;
      ws.onmessage = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    }
    wsRef.current = null;
    activeStreamIdRef.current = null;
    setConnected(false);
  }, []);

  const connect = useCallback(() => {
    const current = wsRef.current;
    if (current && (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (current) {
      disconnect();
    }

    const ws = new WebSocket(`${WS_BASE}/ws/chat/${characterId}/`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      if (wsRef.current === ws) wsRef.current = null;
      setConnected(false);
      activeStreamIdRef.current = null;
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
        } else if (data.type === 'stream_start') {
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
        }
      } catch {
        // ignore non-JSON
      }
    };
    wsRef.current = ws;
  }, [characterId, disconnect]);

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || isStreaming) return;
      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: text.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'message', content: text.trim() }));
        return;
      }

      // fallback: REST SSE
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
    [characterId, isStreaming]
  );

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
    isStreaming,
    connected,
    connect,
    disconnect,
    hydrateMessages,
    removeMessageById,
  };
}
