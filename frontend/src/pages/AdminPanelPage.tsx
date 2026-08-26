import { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { adminApi, type AdminUser } from '@/api/admin';

type ToastState = { text: string; type: 'success' | 'error' } | null;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

export function AdminPanelPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [disabledIds, setDisabledIds] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<ToastState>(null);

  const showToast = useCallback((text: string, type: 'success' | 'error') => {
    setToast({ text, type });
    window.setTimeout(() => setToast(null), 2200);
  }, []);

  useEffect(() => {
    adminApi
      .listUsers()
      .then(setUsers)
      .catch(() => showToast('加载用户列表失败', 'error'))
      .finally(() => setLoading(false));
  }, [showToast]);

  const handleToggle = useCallback(
    async (
      user: AdminUser,
      field: 'can_create_character' | 'can_publish_character'
    ) => {
      const prev = user[field];
      setDisabledIds((s) => new Set(s).add(user.id));
      setUsers((list) =>
        list.map((u) => (u.id === user.id ? { ...u, [field]: !prev } : u))
      );
      try {
        const updated = await adminApi.updateUser(user.id, { [field]: !prev });
        setUsers((list) => list.map((u) => (u.id === updated.id ? updated : u)));
        showToast('权限已更新', 'success');
      } catch (err) {
        setUsers((list) =>
          list.map((u) => (u.id === user.id ? { ...u, [field]: prev } : u))
        );
        showToast(err instanceof Error ? err.message : '更新失败', 'error');
      } finally {
        setDisabledIds((s) => {
          const next = new Set(s);
          next.delete(user.id);
          return next;
        });
      }
    },
    [showToast]
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <motion.div
        className="mb-8"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="font-display text-3xl font-semibold text-soul-ink mb-2">管理后台</h1>
        <p className="text-soul-deep/70">管理用户权限</p>
      </motion.div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 rounded-xl bg-soul-sand/40 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-soul-sand bg-white/80 shadow-sm">
          <table className="w-full text-sm text-soul-ink">
            <thead>
              <tr className="border-b border-soul-sand bg-soul-sand/30 text-soul-deep/70 text-left">
                <th className="px-4 py-3 font-medium">用户名</th>
                <th className="px-4 py-3 font-medium">邮箱</th>
                <th className="px-4 py-3 font-medium">注册时间</th>
                <th className="px-4 py-3 font-medium text-center">角色数</th>
                <th className="px-4 py-3 font-medium text-center">创建角色</th>
                <th className="px-4 py-3 font-medium text-center">发布角色</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-soul-sand/50 last:border-0 hover:bg-soul-sand/20 transition-colors">
                  <td className="px-4 py-3 font-medium">
                    {u.username}
                    {u.is_admin && (
                      <span className="ml-2 text-xs bg-soul-rose/10 text-soul-rose px-1.5 py-0.5 rounded-full">
                        管理员
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-soul-deep/70">{u.email}</td>
                  <td className="px-4 py-3 text-soul-deep/70">{formatDate(u.date_joined)}</td>
                  <td className="px-4 py-3 text-center">{u.character_count}</td>
                  <td className="px-4 py-3 text-center">
                    <Toggle
                      checked={u.can_create_character}
                      disabled={disabledIds.has(u.id)}
                      onChange={() => void handleToggle(u, 'can_create_character')}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Toggle
                      checked={u.can_publish_character}
                      disabled={disabledIds.has(u.id)}
                      onChange={() => void handleToggle(u, 'can_publish_character')}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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

function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled: boolean;
  onChange: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-soul-rose/30 disabled:opacity-50 disabled:cursor-not-allowed ${
        checked ? 'bg-soul-rose' : 'bg-soul-sand'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}
