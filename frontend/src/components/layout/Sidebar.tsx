import { NavLink } from 'react-router-dom';
import { LayoutDashboard, GitBranch, Play, Box, ClipboardList } from 'lucide-react';

const links = [
  { to: '/', icon: LayoutDashboard, label: '대시보드' },
  { to: '/review', icon: GitBranch, label: '코드 리뷰' },
  { to: '/deploy', icon: Play, label: '배포' },
  { to: '/sandbox', icon: Box, label: '샌드박스' },
  { to: '/audit', icon: ClipboardList, label: '감사 로그' },
];

export default function Sidebar() {
  return (
    <aside className="w-60 bg-gray-900 text-gray-300 flex flex-col min-h-screen">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold text-white">SCM Portal</h1>
        <p className="text-xs text-gray-500">Agentic Deployment</p>
      </div>
      <nav className="flex-1 p-2">
        {links.map(({ to, icon: Icon, label }) => (
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
    </aside>
  );
}
