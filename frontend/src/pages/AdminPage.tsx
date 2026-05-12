import { useState, useEffect, useCallback } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { UserCheck, UserX, Shield } from 'lucide-react';
import Header from '../components/layout/Header';
import { listUsers, registerUser, type UserInfo } from '../api/authApi';
import client from '../api/client';

export default function AdminPage() {
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(true);

  // 사용자 등록
  const [showRegister, setShowRegister] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('user');
  const [registerError, setRegisterError] = useState('');

  const loadUsers = useCallback(() => {
    setLoading(true);
    listUsers().then(setUsers).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);
  useAutoRefresh(loadUsers);

  const handleActivate = async (userId: number) => {
    await client.put(`/auth/users/${userId}/activate`);
    loadUsers();
  };

  const handleDeactivate = async (userId: number) => {
    if (!confirm('이 사용자를 비활성화하시겠습니까?')) return;
    await client.put(`/auth/users/${userId}/deactivate`);
    loadUsers();
  };

  const handleRegister = async () => {
    setRegisterError('');
    try {
      await registerUser(newUsername, newPassword, newRole);
      setNewUsername('');
      setNewPassword('');
      setShowRegister(false);
      loadUsers();
    } catch (e: any) {
      setRegisterError(e.response?.data?.detail || '등록 실패');
    }
  };

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <div>
      <Header title="사용자 관리" subtitle="회원 승인 및 등록" />

      {/* 사용자 관리 */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800">사용자 목록 ({users.length})</h3>
          <button
            onClick={() => setShowRegister(!showRegister)}
            className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs hover:bg-green-700"
          >
            + 직접 등록
          </button>
        </div>

        {showRegister && (
          <div className="flex items-end gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
            <div>
              <label className="block text-xs text-gray-500 mb-1">아이디</label>
              <input type="text" value={newUsername} onChange={(e) => setNewUsername(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm w-40" placeholder="username" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">비밀번호</label>
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm w-40" placeholder="password" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">역할</label>
              <select value={newRole} onChange={(e) => setNewRole(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm">
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </div>
            <button onClick={handleRegister} disabled={!newUsername || !newPassword}
              className="px-4 py-1.5 bg-green-600 text-white rounded text-sm disabled:opacity-50">등록</button>
            {registerError && <span className="text-xs text-red-500">{registerError}</span>}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-gray-500 py-4 text-center">로딩 중...</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b">
                <th className="pb-2">ID</th>
                <th className="pb-2">아이디</th>
                <th className="pb-2">역할</th>
                <th className="pb-2">API Key</th>
                <th className="pb-2">상태</th>
                <th className="pb-2">가입일</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b last:border-b-0 hover:bg-gray-50">
                  <td className="py-2.5 font-mono text-xs">{u.id}</td>
                  <td className="py-2.5">
                    <div className="flex items-center gap-1.5">
                      {u.role === 'admin' && <Shield size={12} className="text-purple-500" />}
                      {u.username}
                    </div>
                  </td>
                  <td className="py-2.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="py-2.5">
                    {u.has_llm_credentials ? (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">개별 등록</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">팀 공용</span>
                    )}
                  </td>
                  <td className="py-2.5">
                    {u.is_active ? (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">활성</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">대기</span>
                    )}
                  </td>
                  <td className="py-2.5 text-xs text-gray-500">
                    {new Date(u.created_at).toLocaleDateString('ko-KR')}
                  </td>
                  <td className="py-2.5 text-right">
                    {u.id !== currentUser.id && (
                      u.is_active ? (
                        <button onClick={() => handleDeactivate(u.id)}
                          className="flex items-center gap-1 text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded border border-red-200">
                          <UserX size={12} /> 비활성화
                        </button>
                      ) : (
                        <button onClick={() => handleActivate(u.id)}
                          className="flex items-center gap-1 text-xs px-2 py-1 text-green-600 hover:bg-green-50 rounded border border-green-200">
                          <UserCheck size={12} /> 승인
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
