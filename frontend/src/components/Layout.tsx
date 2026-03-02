import { Outlet, Link, useLocation } from 'react-router-dom';
// 1. 在顶部引入 BarChart2 图标
import { Heart, LayoutGrid, LogIn, LogOut, UserPlus, BarChart2 } from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';



const nav = [
  { to: '/', label: '首页', icon: Heart },
  { to: '/plaza', label: '角色广场', icon: LayoutGrid },
  { to: '/dashboard', label: '数据洞察', icon: BarChart2 }, // <--- 新增这行
  { to: '/register', label: '创建账号', icon: UserPlus },
];


export function Layout() {
  const location = useLocation();
  const { user, loading, logout } = useAuth();

  const hideFooter = location.pathname.startsWith('/chat');

  return (
    <div className="h-dvh overflow-hidden flex flex-col">
      <header className="sticky top-0 z-50 border-b border-soul-sand/80 bg-soul-cream/90 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-soul-deep hover:text-soul-rose transition-colors">
            <Heart className="w-6 h-6 text-soul-rose" strokeWidth={1.5} />
            <span className="font-display text-xl font-semibold tracking-tight">AI 灵魂伴侣</span>
          </Link>
          <nav className="flex items-center gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  location.pathname === to
                    ? 'bg-soul-rose/10 text-soul-rose'
                    : 'text-soul-deep/80 hover:bg-soul-sand/60 hover:text-soul-deep'
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
            <span className="w-px h-5 bg-soul-sand mx-1" />
            {loading ? (
              <span className="text-xs text-soul-deep/60 px-2">加载中...</span>
            ) : user ? (
              <>
                <span className="text-sm text-soul-deep/80 px-2">你好，{user.username}</span>
                <button
                  type="button"
                  onClick={() => void logout()}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-soul-deep/80 hover:bg-soul-sand/60"
                >
                  <LogOut className="w-4 h-4" />
                  退出
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-soul-deep/80 hover:bg-soul-sand/60"
              >
                <LogIn className="w-4 h-4" />
                登录
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1 min-h-0 overflow-hidden">
        <Outlet />
      </main>

      {!hideFooter && (
        <footer className="border-t border-soul-sand/80 py-6 text-center text-soul-deep/60 text-sm font-body">
          AI 灵魂伴侣 · 与虚拟角色深度互动
        </footer>
      )}
    </div>
  );
}