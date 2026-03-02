import { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { charactersApi } from '@/api/characters';
import { CharacterCard } from '@/components/CharacterCard';
import { useAuth } from '@/context/AuthContext';
import type { Character } from '@/types';

type ToastState = {
  text: string;
  type: 'success' | 'error';
} | null;

export function PlazaPage() {
  const { user } = useAuth();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<Character | null>(null);
  const [toast, setToast] = useState<ToastState>(null);

  const showToast = useCallback((text: string, type: 'success' | 'error') => {
    setToast({ text, type });
    window.setTimeout(() => setToast(null), 2200);
  }, []);

  const loadCharacters = useCallback(async () => {
    setLoading(true);
    try {
      const list = await charactersApi.list({ is_public: true, search: search || undefined });
      setCharacters(list);
    } catch {
      setCharacters([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void loadCharacters();
  }, [loadCharacters]);

  const handleDelete = useCallback(async () => {
    if (!confirmTarget) return;
    setDeletingId(confirmTarget.id);
    try {
      await charactersApi.delete(confirmTarget.id);
      await loadCharacters();
      showToast('角色已删除', 'success');
    } catch (err) {
      showToast(err instanceof Error ? err.message : '删除失败，请稍后重试', 'error');
    } finally {
      setDeletingId(null);
      setConfirmTarget(null);
    }
  }, [confirmTarget, loadCharacters, showToast]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <motion.div
        className="mb-10"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="font-display text-3xl font-semibold text-soul-ink mb-2">角色广场</h1>
        <p className="text-soul-deep/70">发现并开始与大家分享的虚拟角色对话</p>
        <div className="mt-6">
          <input
            type="search"
            placeholder="搜索角色名称或标签…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md px-4 py-2.5 rounded-xl border border-soul-sand bg-white/80 text-soul-ink placeholder:text-soul-deep/50 focus:outline-none focus:ring-2 focus:ring-soul-rose/30 focus:border-soul-rose"
          />
        </div>
      </motion.div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl bg-soul-sand/40 aspect-[4/5] animate-pulse"
            />
          ))}
        </div>
      ) : characters.length === 0 ? (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-soul-deep/60 text-center py-16"
        >
          暂无公开角色，去创建一个吧 →
        </motion.p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {characters.map((c, i) => (
            <CharacterCard
              key={c.id}
              character={c}
              index={i}
              canDelete={!!user && c.creator_id === user.id}
              deleting={deletingId === c.id}
              onRequestDelete={(char) => setConfirmTarget(char)}
            />
          ))}
        </div>
      )}

      <AnimatePresence>
        {confirmTarget && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/35 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.98, opacity: 0 }}
              className="w-full max-w-sm rounded-2xl bg-white border border-soul-sand shadow-xl p-5"
            >
              <h3 className="font-display text-lg text-soul-ink">确认删除角色？</h3>
              <p className="text-sm text-soul-deep/70 mt-2">
                删除后无法恢复：{confirmTarget.name}
              </p>
              <div className="mt-5 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmTarget(null)}
                  className="px-3 py-2 rounded-lg border border-soul-sand text-soul-deep hover:bg-soul-sand/30"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete()}
                  disabled={deletingId === confirmTarget.id}
                  className="px-3 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-60"
                >
                  {deletingId === confirmTarget.id ? '删除中…' : '确认删除'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className={`fixed right-4 top-16 z-[60] px-4 py-2 rounded-xl shadow-lg text-sm ${
              toast.type === 'success'
                ? 'bg-emerald-500 text-white'
                : 'bg-red-500 text-white'
            }`}
          >
            {toast.text}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
