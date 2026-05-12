import { useState } from 'react';
import { Lock } from 'lucide-react';
import Header from '../components/layout/Header';
import client from '../api/client';

export default function SettingsPage() {
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwMsg, setPwMsg] = useState('');
  const [pwSaving, setPwSaving] = useState(false);

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const handleChangePassword = async () => {
    setPwMsg('');
    if (newPw !== confirmPw) {
      setPwMsg('새 비밀번호가 일치하지 않습니다.');
      return;
    }
    if (newPw.length < 4) {
      setPwMsg('비밀번호는 4자 이상이어야 합니다.');
      return;
    }
    setPwSaving(true);
    try {
      await client.put('/auth/me/password', {
        current_password: currentPw,
        new_password: newPw,
      });
      setPwMsg('비밀번호가 변경되었습니다.');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (e: any) {
      setPwMsg(e.response?.data?.detail || '변경 실패');
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <div>
      <Header title="설정" subtitle="계정 설정" />

      <div className="max-w-xl space-y-6">
        {/* 계정 정보 */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">계정 정보</h3>
          <div className="text-sm space-y-1">
            <p><span className="text-gray-500">아이디:</span> <span className="font-medium">{user.username}</span></p>
            <p><span className="text-gray-500">역할:</span> <span className="font-medium">{user.role}</span></p>
          </div>
          <p className="mt-3 text-xs text-gray-400">
            LLM은 시스템 단일 client_credentials 방식으로 호출됩니다. 사용자별 API Key 등록은 필요하지 않습니다.
          </p>
        </div>

        {/* 비밀번호 변경 */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Lock size={16} className="text-gray-600" />
            <h3 className="text-sm font-semibold text-gray-700">비밀번호 변경</h3>
          </div>
          <div className="space-y-3">
            <input
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              placeholder="현재 비밀번호"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="새 비밀번호"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <input
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              placeholder="새 비밀번호 확인"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <button
              onClick={handleChangePassword}
              disabled={!currentPw || !newPw || !confirmPw || pwSaving}
              className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm hover:bg-gray-900 disabled:opacity-50"
            >
              {pwSaving ? '변경 중...' : '비밀번호 변경'}
            </button>
          </div>
          {pwMsg && <p className={`mt-2 text-sm ${pwMsg.includes('실패') || pwMsg.includes('일치') || pwMsg.includes('올바르지') ? 'text-red-600' : 'text-green-600'}`}>{pwMsg}</p>}
        </div>
      </div>
    </div>
  );
}
