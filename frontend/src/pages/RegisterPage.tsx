import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(username.trim(), email.trim(), password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败，用户名或邮箱可能已被使用');
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
        <h1 className="font-display text-2xl font-semibold text-soul-ink mb-2">注册</h1>
        <p className="text-soul-deep/70 text-sm mb-6">创建账号，开始你的灵魂伴侣之旅</p>
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
            <label className="block text-sm font-medium text-soul-deep mb-1">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              minLength={6}
            />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-soul-rose text-white font-medium hover:bg-soul-terracotta disabled:opacity-60"
          >
            {loading ? '注册中…' : '注册'}
          </button>
        </form>
        <p className="mt-4 text-center text-soul-deep/70 text-sm">
          已有账号？ <Link to="/login" className="text-soul-rose hover:underline">登录</Link>
        </p>
      </motion.div>
    </div>
  );
}
