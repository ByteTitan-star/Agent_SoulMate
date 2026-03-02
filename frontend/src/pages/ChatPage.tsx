import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Bot,
  Brain,
  Clock3,
  History,
  Mic,
  MicOff,
  Send,
  Trash2,
  X,
} from 'lucide-react';
import { charactersApi } from '@/api/characters';
import { chatApi } from '@/api/chat';
import { useChat } from '@/hooks/useChat';
import { useAuth } from '@/context/AuthContext';
import type { Character, Message } from '@/types';

const DEFAULT_TOOL_ROLE_NAMES = new Set(['晴空天气官', '今日资讯官', '知识库馆长']);

function isDefaultToolRole(char: Character): boolean {
  if (DEFAULT_TOOL_ROLE_NAMES.has(char.name)) return true;
  const personality = Array.isArray(char.personality) ? char.personality : [];
  return personality.includes('系统角色') || personality.includes('工具代理');
}

function formatTimestamp(value?: string): string {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ChatPage() {
  const { characterId } = useParams<{ characterId: string }>();
  const { user } = useAuth();
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);
  const [historyEntries, setHistoryEntries] = useState<Message[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [toolRoles, setToolRoles] = useState<Character[]>([]);
  const [deletingMap, setDeletingMap] = useState<Record<string, boolean>>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const {
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
  } = useChat(characterId ?? '');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wasStreamingRef = useRef(false);
  const [voiceActive, setVoiceActive] = useState(false);

  const loadHistory = useCallback(
    async (withLoading: boolean) => {
      if (!characterId || !user) {
        setHistoryEntries([]);
        hydrateMessages([]);
        if (withLoading) setHistoryLoading(false);
        return;
      }
      if (withLoading) setHistoryLoading(true);
      try {
        const resp = await chatApi.listHistory(characterId);
        setHistoryEntries(resp.items ?? []);
        hydrateMessages(resp.items ?? []);
      } catch {
        setHistoryEntries([]);
        hydrateMessages([]);
      } finally {
        if (withLoading) setHistoryLoading(false);
      }
    },
    [characterId, hydrateMessages, user]
  );

  useEffect(() => {
    if (!characterId) return;
    charactersApi
      .get(characterId)
      .then(setCharacter)
      .catch(() => setCharacter(null))
      .finally(() => setLoading(false));
  }, [characterId]);

  useEffect(() => {
    if (!characterId) return;
    connect();
    return () => disconnect();
  }, [characterId, connect, disconnect]);

  useEffect(() => {
    void loadHistory(true);
  }, [loadHistory]);

  useEffect(() => {
    if (!characterId || !user) return;
    if (wasStreamingRef.current && !isStreaming) {
      void loadHistory(false);
    }
    wasStreamingRef.current = isStreaming;
  }, [characterId, isStreaming, loadHistory, user]);

  useEffect(() => {
    if (!user) {
      setToolRoles([]);
      return;
    }
    charactersApi
      .myList()
      .then((list) => {
        const defaults = (list ?? []).filter(isDefaultToolRole).slice(0, 3);
        setToolRoles(defaults);
      })
      .catch(() => setToolRoles([]));
  }, [user]);

  useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(() => setFeedback(null), 1800);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleDeleteHistory = async (messageId: string) => {
    if (!characterId || !user) return;
    const ok = window.confirm('确认删除这条会话记录？');
    if (!ok) return;
    setDeletingMap((prev) => ({ ...prev, [messageId]: true }));
    try {
      await chatApi.deleteHistoryMessage(characterId, messageId);
      setHistoryEntries((prev) => prev.filter((m) => m.id !== messageId));
      removeMessageById(messageId);
      setFeedback('历史消息已删除');
    } catch (error) {
      const detail = error instanceof Error ? error.message : '删除失败';
      setFeedback(detail);
    } finally {
      setDeletingMap((prev) => {
        const next = { ...prev };
        delete next[messageId];
        return next;
      });
    }
  };

  const memoryStats = useMemo(() => {
    const total = historyEntries.length;
    const userTurns = historyEntries.filter((m) => m.role === 'user').length;
    const assistantTurns = historyEntries.filter((m) => m.role === 'assistant').length;
    const latest = total > 0 ? historyEntries[total - 1]?.timestamp : '';
    return { total, userTurns, assistantTurns, latest };
  }, [historyEntries]);

  if (loading) {
    return (
      <div className="mx-auto flex max-w-2xl justify-center px-4 py-16">
        <div className="w-10 h-10 rounded-full border-2 border-soul-rose border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!character) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <p className="text-soul-deep/70 mb-4">未找到该角色</p>
        <Link to="/plaza" className="text-soul-rose hover:underline">
          返回角色广场
        </Link>
      </div>
    );
  }

  return (
    <>
      {/* <div className="mx-auto w-full max-w-[1360px] px-4 pb-6 pt-4 lg:px-6"> */}
      <div className="h-full flex flex-col pb-4">
        <div className="mx-auto w-full max-w-[1360px] px-4 pt-4 lg:px-6 flex-1 min-h-0">
          <div className="grid h-full gap-5 xl:grid-cols-12">
            <aside className="hidden xl:col-span-3 xl:flex xl:flex-col xl:gap-4 overflow-y-auto">
              <div className="rounded-2xl border border-soul-sand/70 bg-white/85 p-4 shadow-[0_10px_24px_rgba(0,0,0,0.04)]">
                <div className="mb-3 flex items-center gap-2">
                  <Brain className="h-4 w-4 text-soul-sage" />
                  <h3 className="text-sm font-semibold text-soul-ink">会话记忆</h3>
                </div>
                <p className="text-xs text-soul-deep/70">本角色的历史对话会自动写入记忆，用于后续连续交流。</p>
                <div className="mt-3 space-y-2 text-xs text-soul-deep/80">
                  <p>总消息数：{memoryStats.total}</p>
                  <p>用户发言：{memoryStats.userTurns}</p>
                  <p>助手回复：{memoryStats.assistantTurns}</p>
                  <p>最近更新：{formatTimestamp(memoryStats.latest)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setHistoryOpen(true)}
                  className="mt-4 w-full rounded-xl border border-soul-sand bg-soul-cream/80 px-3 py-2 text-xs font-medium text-soul-deep hover:bg-soul-sand/60"
                >
                  查看全部历史
                </button>
              </div>

              <div className="rounded-2xl border border-soul-sand/70 bg-white/85 p-4 shadow-[0_10px_24px_rgba(0,0,0,0.04)]">
                <div className="mb-3 flex items-center gap-2">
                  <Bot className="h-4 w-4 text-soul-rose" />
                  <h3 className="text-sm font-semibold text-soul-ink">系统工具角色</h3>
                </div>
                {toolRoles.length === 0 ? (
                  <p className="text-xs text-soul-deep/70">登录后会自动生成 3 个工具角色（天气/资讯/知识库）。</p>
                ) : (
                  <div className="space-y-3">
                    {toolRoles.map((role) => (
                      <Link
                        key={role.id}
                        to={`/chat/${role.id}`}
                        className="flex items-center gap-3 rounded-xl border border-soul-sand/70 bg-soul-cream/70 p-2 hover:bg-soul-sand/60"
                      >
                        <div className="h-10 w-10 overflow-hidden rounded-lg bg-soul-sand/70">
                          {role.avatar_url ? (
                            <img src={role.avatar_url} alt={role.name} className="h-full w-full object-cover" />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center text-soul-sage">
                              {role.name.charAt(0)}
                            </div>
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-soul-ink">{role.name}</p>
                          <p className="truncate text-[11px] text-soul-deep/70">
                            {role.opening_message || '点击切换对话'}
                          </p>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </aside>

            {/* <section className="xl:col-span-9"> */}
            <section className="xl:col-span-9 flex flex-col min-h-0 h-full">
              <div className="mx-auto flex flex-1 min-h-0 w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-soul-sand/70 bg-white/90 shadow-[0_16px_40px_rgba(28,25,23,0.08)]">
                <motion.header
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-3 border-b border-soul-sand/60 px-4 py-3 sm:px-6"
                >
                  <Link
                    to="/plaza"
                    className="rounded-lg p-2 text-soul-deep/70 hover:bg-soul-sand/50 hover:text-soul-deep"
                  >
                    <ArrowLeft className="h-5 w-5" />
                  </Link>
                  <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-xl bg-soul-sand/60">
                    {character.avatar_url ? (
                      <img src={character.avatar_url} alt={character.name} className="h-full w-full object-cover" />
                    ) : (
                      <span className="flex h-full w-full items-center justify-center font-display text-xl text-soul-sage">
                        {character.name.charAt(0)}
                      </span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h1 className="truncate font-display text-lg font-semibold text-soul-ink">{character.name}</h1>
                    <p className="text-xs text-soul-deep/60">{connected ? '已连接' : '连接中'} · 文字与语音对话</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setHistoryOpen(true)}
                    className="inline-flex items-center gap-1 rounded-lg border border-soul-sand bg-soul-cream/80 px-3 py-1.5 text-xs text-soul-deep hover:bg-soul-sand/60"
                  >
                    <History className="h-4 w-4" />
                    历史
                  </button>
                </motion.header>

                <div className="relative flex flex-col flex-1 min-h-0 px-2 pb-3 pt-4 sm:px-5">
                  <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-3 pt-4 sm:px-5 scrollbar-soft scrollbar-gutter-stable">
                    <div className="space-y-4 pb-1 pr-2 sm:pr-4">
                      <AnimatePresence initial={false}>
                        {messages.length === 0 && (
                          <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="py-10 text-center text-sm text-soul-deep/55"
                          >
                            {historyLoading
                              ? '正在加载会话记忆...'
                              : character.opening_message?.trim() || '发一条消息开始对话'}
                          </motion.p>
                        )}
                        {messages.map((msg) => (
                          <motion.div
                            key={msg.id}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
                          >
                            <div
                              className={
                                msg.role === 'user'
                                  ? 'max-w-[85%] rounded-2xl rounded-br-md bg-soul-rose px-4 py-2.5 text-white'
                                  : 'max-w-[85%] rounded-2xl rounded-bl-md border border-soul-sand/80 bg-soul-cream/70 px-4 py-2.5 text-soul-ink'
                              }
                            >
                              <p className="whitespace-pre-wrap break-words text-sm leading-6">{msg.content || '...'}</p>
                            </div>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                      <div ref={messagesEndRef} />
                    </div>
                  </div>
                </div>

                <motion.form
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  onSubmit={handleSubmit}
                  className="flex-shrink-0 flex gap-2 border-t border-soul-sand/60 px-4 py-4 sm:px-6"
                >
                  <button
                    type="button"
                    onClick={() => setVoiceActive((v) => !v)}
                    className={`flex-shrink-0 rounded-xl p-3 transition-colors ${voiceActive ? 'bg-soul-rose text-white' : 'bg-soul-sand/50 text-soul-deep hover:bg-soul-sand'
                      }`}
                    title={voiceActive ? '结束语音' : '开始语音'}
                  >
                    {voiceActive ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                  </button>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="输入消息..."
                    disabled={isStreaming}
                    className="flex-1 rounded-xl border border-soul-sand bg-white px-4 py-3 text-soul-ink placeholder:text-soul-deep/50 focus:outline-none focus:ring-2 focus:ring-soul-rose/30 disabled:opacity-60"
                  />
                  <button
                    type="submit"
                    disabled={isStreaming || !input.trim()}
                    className="flex-shrink-0 rounded-xl bg-soul-rose p-3 text-white transition-colors hover:bg-soul-terracotta disabled:opacity-50"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </motion.form>
              </div>
            </section>
          </div>
        </div>
      </div>

      {feedback && (
        <div className="fixed bottom-6 left-1/2 z-[80] -translate-x-1/2 rounded-xl border border-soul-sand bg-white/95 px-4 py-2 text-sm text-soul-ink shadow-lg">
          {feedback}
        </div>
      )}

      {historyOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-soul-ink/45 p-4">
          <div className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-soul-sand/80 bg-soul-cream shadow-2xl">
            <header className="flex items-center justify-between border-b border-soul-sand/70 px-5 py-3">
              <div>
                <h3 className="text-base font-semibold text-soul-ink">会话全部历史</h3>
                <p className="mt-0.5 text-xs text-soul-deep/65">
                  <Clock3 className="mr-1 inline-block h-3.5 w-3.5" />
                  共 {historyEntries.length} 条
                </p>
              </div>
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="rounded-lg p-2 text-soul-deep/70 hover:bg-soul-sand/60"
              >
                <X className="h-5 w-5" />
              </button>
            </header>
            <div className="scrollbar-soft scrollbar-gutter-stable flex-1 overflow-y-auto px-5 py-4 pr-7">
              {historyEntries.length === 0 ? (
                <p className="rounded-xl border border-dashed border-soul-sand/80 bg-white/60 px-4 py-6 text-center text-sm text-soul-deep/65">
                  当前没有历史记录
                </p>
              ) : (
                <div className="space-y-3">
                  {historyEntries.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-soul-sand/70 bg-white/80 px-4 py-3"
                    >
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${item.role === 'user'
                              ? 'bg-soul-rose/12 text-soul-rose'
                              : 'bg-soul-sage/18 text-soul-deep'
                              }`}
                          >
                            {item.role === 'user' ? '用户' : '角色'}
                          </span>
                          <span className="text-[11px] text-soul-deep/60">{formatTimestamp(item.timestamp)}</span>
                        </div>
                        <button
                          type="button"
                          disabled={Boolean(deletingMap[item.id])}
                          onClick={() => void handleDeleteHistory(item.id)}
                          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          删除
                        </button>
                      </div>
                      <p className="whitespace-pre-wrap break-words text-sm leading-6 text-soul-ink">{item.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
