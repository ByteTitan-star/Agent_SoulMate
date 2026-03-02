import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-soul-sand/80 bg-white/80 shadow-lg p-8"
      >
        <h1 className="font-display text-2xl font-semibold text-soul-ink mb-2">登录</h1>
        <p className="text-soul-deep/70 text-sm mb-6">登录后即可创建角色并与 TA 对话</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-soul-sand bg-white text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-soul-sand bg-white text-soul-ink focus:outline-none focus:ring-2 focus:ring-soul-rose/30"
              required
            />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-soul-rose text-white font-medium hover:bg-soul-terracotta disabled:opacity-60"
          >
            {loading ? '登录中…' : '登录'}
          </button>
        </form>
        <p className="mt-4 text-center text-soul-deep/70 text-sm">
          还没有账号？ <Link to="/register" className="text-soul-rose hover:underline">注册</Link>
        </p>
      </motion.div>
    </div>
  );
}
