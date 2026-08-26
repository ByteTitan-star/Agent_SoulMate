import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { charactersApi, type UpdateCharacterPayload } from '@/api/characters';
import { useAuth } from '@/context/AuthContext';
import type { Character } from '@/types';

type ToastState = { text: string; type: 'success' | 'error' } | null;

const GENDER_LABELS: Record<string, string> = {
  male: '男',
  female: '女',
  other: '其他',
};

export function MyCharactersPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<ToastState>(null);
  const [confirmTarget, setConfirmTarget] = useState<Character | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<Character | null>(null);

  const showToast = useCallback((text: string, type: 'success' | 'error') => {
    setToast({ text, type });
    window.setTimeout(() => setToast(null), 2200);
  }, []);

  const loadCharacters = useCallback(async () => {
    setLoading(true);
    try {
      const list = await charactersApi.myList();
      setCharacters(list);
    } catch {
      showToast('加载角色列表失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void loadCharacters();
  }, [loadCharacters]);

  const handleDelete = useCallback(async () => {
    if (!confirmTarget) return;
    setDeletingId(confirmTarget.id);
    try {
      await charactersApi.delete(confirmTarget.id);
      setCharacters((list) => list.filter((c) => c.id !== confirmTarget.id));
      showToast('角色已删除', 'success');
    } catch (err) {
      showToast(err instanceof Error ? err.message : '删除失败', 'error');
    } finally {
      setDeletingId(null);
      setConfirmTarget(null);
    }
  }, [confirmTarget, showToast]);

  const handlePublish = useCallback(
    async (character: Character, isPublic: boolean) => {
      try {
        const updated = await charactersApi.update(character.id, { is_public: isPublic });
        setCharacters((list) => list.map((c) => (c.id === updated.id ? updated : c)));
        showToast(isPublic ? '角色已发布' : '角色已下架', 'success');
      } catch (err) {
        showToast(err instanceof Error ? err.message : '操作失败', 'error');
      }
    },
    [showToast]
  );

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="rounded-2xl bg-soul-sand/40 aspect-[4/5] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <motion.div
        className="mb-8"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="font-display text-3xl font-semibold text-soul-ink mb-2">我的角色</h1>
        <p className="text-soul-deep/70">管理你创建的所有角色</p>
      </motion.div>

      {characters.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-20"
        >
          <p className="text-soul-deep/60 mb-4">你还没有创建任何角色</p>
          <Link
            to="/create"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-soul-rose text-white text-sm font-medium hover:bg-soul-rose/90 transition-colors"
          >
            去创建
          </Link>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {characters.map((c, i) => (
            <CharacterCard
              key={c.id}
              character={c}
              index={i}
              canPublish={!!user?.can_publish_character}
              onPreview={() => navigate(`/chat/${c.id}`)}
              onEdit={() => setEditTarget(c)}
              onDelete={() => setConfirmTarget(c)}
              onPublish={() => void handlePublish(c, true)}
              onUnpublish={() => void handlePublish(c, false)}
            />
          ))}
        </div>
      )}

      {/* 删除确认对话框 */}
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
              <p className="text-sm text-soul-deep/70 mt-2">删除后无法恢复：{confirmTarget.name}</p>
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

      {/* 内联编辑表单 */}
      <AnimatePresence>
        {editTarget && (
          <EditModal
            character={editTarget}
            onClose={() => setEditTarget(null)}
            onSaved={(updated) => {
              setCharacters((list) => list.map((c) => (c.id === updated.id ? updated : c)));
              setEditTarget(null);
              showToast('角色已更新', 'success');
            }}
            onError={(msg) => showToast(msg, 'error')}
          />
        )}
      </AnimatePresence>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className={`fixed right-4 top-16 z-[60] px-4 py-2 rounded-xl shadow-lg text-sm ${
              toast.type === 'success' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
            }`}
          >
            {toast.text}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── 角色卡片 ── */
function CharacterCard({
  character: c,
  index,
  canPublish,
  onPreview,
  onEdit,
  onDelete,
  onPublish,
  onUnpublish,
}: {
  character: Character;
  index: number;
  canPublish: boolean;
  onPreview: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onPublish: () => void;
  onUnpublish: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-2xl border border-soul-sand bg-white/80 shadow-sm overflow-hidden flex flex-col"
    >
      {/* 头像 */}
      <div className="relative aspect-square bg-soul-sand/30">
        {c.avatar_url ? (
          <img src={c.avatar_url} alt={c.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl text-soul-deep/30">
            {c.name[0]}
          </div>
        )}
        <span
          className={`absolute top-2 right-2 text-xs px-2 py-0.5 rounded-full font-medium ${
            c.is_public
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-soul-sand text-soul-deep/60'
          }`}
        >
          {c.is_public ? '已发布' : '未发布'}
        </span>
      </div>

      {/* 信息 */}
      <div className="p-3 flex-1 flex flex-col gap-2">
        <div>
          <p className="font-medium text-soul-ink truncate">{c.name}</p>
          <p className="text-xs text-soul-deep/60">{GENDER_LABELS[c.gender] ?? c.gender}</p>
        </div>

        {/* 操作按钮 */}
        <div className="flex flex-wrap gap-1.5 mt-auto">
          <button
            type="button"
            onClick={onPreview}
            className="flex-1 min-w-0 px-2 py-1.5 rounded-lg text-xs bg-soul-sand/50 text-soul-deep hover:bg-soul-sand transition-colors"
          >
            预览
          </button>
          <button
            type="button"
            onClick={onEdit}
            className="flex-1 min-w-0 px-2 py-1.5 rounded-lg text-xs bg-soul-rose/10 text-soul-rose hover:bg-soul-rose/20 transition-colors"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="flex-1 min-w-0 px-2 py-1.5 rounded-lg text-xs bg-red-50 text-red-500 hover:bg-red-100 transition-colors"
          >
            删除
          </button>
        </div>

        {/* 发布/下架 */}
        {c.is_public ? (
          <button
            type="button"
            onClick={onUnpublish}
            className="w-full px-2 py-1.5 rounded-lg text-xs border border-soul-sand text-soul-deep/70 hover:bg-soul-sand/30 transition-colors"
          >
            下架
          </button>
        ) : canPublish ? (
          <button
            type="button"
            onClick={onPublish}
            className="w-full px-2 py-1.5 rounded-lg text-xs bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
          >
            发布
          </button>
        ) : (
          <p className="text-xs text-soul-deep/50 text-center py-1">发布权限已被限制</p>
        )}
      </div>
    </motion.div>
  );
}

/* ── 编辑弹窗 ── */
function EditModal({
  character,
  onClose,
  onSaved,
  onError,
}: {
  character: Character;
  onClose: () => void;
  onSaved: (c: Character) => void;
  onError: (msg: string) => void;
}) {
  const [form, setForm] = useState<UpdateCharacterPayload>({
    name: character.name,
    gender: character.gender,
    system_prompt: character.system_prompt,
    opening_message: character.opening_message ?? '',
    personality: [...character.personality],
    is_public: character.is_public,
  });
  const [tagInput, setTagInput] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await charactersApi.update(character.id, form);
      onSaved(updated);
    } catch (err) {
      onError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.personality?.includes(tag)) {
      setForm((f) => ({ ...f, personality: [...(f.personality ?? []), tag] }));
    }
    setTagInput('');
  };

  const removeTag = (tag: string) => {
    setForm((f) => ({ ...f, personality: (f.personality ?? []).filter((t) => t !== tag) }));
  };

  return (
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
        className="w-full max-w-lg rounded-2xl bg-white border border-soul-sand shadow-xl p-6 overflow-y-auto max-h-[90vh]"
      >
        <h3 className="font-display text-xl text-soul-ink mb-5">编辑角色</h3>

        <div className="space-y-4">
          <Field label="名称">
            <input
              value={form.name ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="w-full px-3 py-2 rounded-xl border border-soul-sand bg-white/80 text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30 focus:border-soul-rose text-sm"
            />
          </Field>

          <Field label="性别">
            <select
              value={form.gender ?? 'other'}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  gender: e.target.value as 'male' | 'female' | 'other',
                }))
              }
              className="w-full px-3 py-2 rounded-xl border border-soul-sand bg-white/80 text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30 focus:border-soul-rose text-sm"
            >
              <option value="male">男</option>
              <option value="female">女</option>
              <option value="other">其他</option>
            </select>
          </Field>

          <Field label="系统提示词">
            <textarea
              rows={4}
              value={form.system_prompt ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, system_prompt: e.target.value }))}
              className="w-full px-3 py-2 rounded-xl border border-soul-sand bg-white/80 text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30 focus:border-soul-rose text-sm resize-none"
            />
          </Field>

          <Field label="开场白">
            <textarea
              rows={2}
              value={form.opening_message ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, opening_message: e.target.value }))}
              className="w-full px-3 py-2 rounded-xl border border-soul-sand bg-white/80 text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30 focus:border-soul-rose text-sm resize-none"
            />
          </Field>

          <Field label="性格标签">
            <div className="flex flex-wrap gap-1.5 mb-2">
              {(form.personality ?? []).map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-soul-rose/10 text-soul-rose text-xs"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    className="hover:text-red-500"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="输入标签后按 Enter"
                className="w-full px-3 py-2 rounded-xl border border-soul-sand bg-white/80 text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30 focus:border-soul-rose text-sm flex-1"
              />
              <button
                type="button"
                onClick={addTag}
                className="px-3 py-2 rounded-lg bg-soul-sand/50 text-soul-deep text-sm hover:bg-soul-sand"
              >
                添加
              </button>
            </div>
          </Field>

          <Field label="公开状态">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_public ?? false}
                onChange={(e) => setForm((f) => ({ ...f, is_public: e.target.checked }))}
                className="w-4 h-4 accent-soul-rose"
              />
              <span className="text-sm text-soul-deep">公开此角色</span>
            </label>
          </Field>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-soul-sand text-soul-deep hover:bg-soul-sand/30 text-sm"
          >
            取消
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-soul-rose text-white hover:bg-soul-rose/90 disabled:opacity-60 text-sm"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-soul-deep/80 mb-1">{label}</label>
      {children}
    </div>
  );
}
