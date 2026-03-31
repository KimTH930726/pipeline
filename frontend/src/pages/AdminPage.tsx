import { useState, useEffect } from 'react';
import { UserCheck, UserX, Shield, Key } from 'lucide-react';
import Header from '../components/layout/Header';
import { listUsers, registerUser, updateApiKey, type UserInfo } from '../api/authApi';
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

  // 내 API Key
  const [myApiKey, setMyApiKey] = useState('');
  const [keyMsg, setKeyMsg] = useState('');

  const loadUsers = () => {
    setLoading(true);
    listUsers().then(setUsers).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadUsers(); }, []);

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

  const handleUpdateKey = async () => {
    if (!myApiKey.trim()) return;
    try {
      await updateApiKey(myApiKey.trim());
      setKeyMsg('API Key가 업데이트되었습니다.');
      setMyApiKey('');
      setTimeout(() => setKeyMsg(''), 3000);
    } catch {
      setKeyMsg('업데이트 실패');
    }
  };

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <div>
      <Header title="사용자 관리" subtitle="회원 승인, 등록 및 API Key 관리" />

      {/* 내 API Key 설정 */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Key size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">내 LLM API Key</h3>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="password"
            value={myApiKey}
            onChange={(e) => setMyApiKey(e.target.value)}
            placeholder="DevX MCP API Key 입력"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          <button
            onClick={handleUpdateKey}
            disabled={!myApiKey.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            저장
          </button>
        </div>
        {keyMsg && <p className="mt-2 text-sm text-green-600">{keyMsg}</p>}
        <p className="mt-2 text-xs text-gray-400">AI 분석(영향도, 코드리뷰, RCA) 호출 시 사용됩니다. 미설정 시 시스템 키로 fallback.</p>
      </div>

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
                    {u.has_api_key ? (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">등록됨</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">미등록</span>
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
