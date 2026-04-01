import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, GitBranch, GitPullRequest, Play, Box, ClipboardList, LogOut, User, Users, Settings, BookOpen } from 'lucide-react';

const links = [
  { to: '/', icon: LayoutDashboard, label: '대시보드' },
  { to: '/branches', icon: GitBranch, label: '브랜치 관리' },
  { to: '/review', icon: GitPullRequest, label: '코드 리뷰' },
  { to: '/sandbox', icon: Box, label: '샌드박스' },
  { to: '/deploy', icon: Play, label: '배포' },
  { to: '/history', icon: ClipboardList, label: '배포 이력' },
  { to: '/guide', icon: BookOpen, label: '시작 가이드' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <aside className="w-60 bg-gray-900 text-gray-300 flex flex-col min-h-screen">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold text-white">Agentic Deployment</h1>
        <p className="text-xs text-gray-500">StarbucksCSP</p>
      </div>
      <nav className="flex-1 p-2">
        {(user?.role === 'admin' ? [...links, { to: '/admin', icon: Users, label: '사용자 관리' }] : links).map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive ? 'bg-blue-600 text-white' : 'hover:bg-gray-800'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      {user && (
        <div className="p-3 border-t border-gray-700">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <User size={16} className="text-gray-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{user.username}</p>
              <p className="text-xs text-gray-500">{user.role}</p>
            </div>
            <NavLink to="/settings" className="text-gray-500 hover:text-white" title="설정">
              <Settings size={16} />
            </NavLink>
            <button onClick={handleLogout} className="text-gray-500 hover:text-white" title="로그아웃">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
