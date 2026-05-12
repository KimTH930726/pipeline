import { useEffect, useState } from 'react';
import { Key, Lock } from 'lucide-react';
import Header from '../components/layout/Header';
import client from '../api/client';
import { updateLLMCredentials, getMe } from '../api/authApi';

export default function SettingsPage() {
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [llmUserId, setLlmUserId] = useState('');
  const [credSaving, setCredSaving] = useState(false);
  const [credMsg, setCredMsg] = useState('');
  const [hasCreds, setHasCreds] = useState(false);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwMsg, setPwMsg] = useState('');
  const [pwSaving, setPwSaving] = useState(false);

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    getMe().then((u) => {
      setHasCreds(u.has_llm_credentials);
      setLlmUserId(u.llm_user_id || '');
    }).catch(() => { /* ignore */ });
  }, []);

  const handleSaveCreds = async () => {
    setCredSaving(true);
    setCredMsg('');
    try {
      await updateLLMCredentials({
        client_id: clientId,
        client_secret: clientSecret,
        llm_user_id: llmUserId,
      });
      setCredMsg('LLM 자격증명이 저장되었습니다.');
      setClientId('');
      setClientSecret('');
      const u = await getMe();
      setHasCreds(u.has_llm_credentials);
    } catch {
      setCredMsg('저장 실패');
    } finally {
      setCredSaving(false);
    }
  };

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
      <Header title="설정" subtitle="계정 + LLM 자격증명" />

      <div className="max-w-xl space-y-6">
        {/* 계정 정보 */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">계정 정보</h3>
          <div className="text-sm space-y-1">
            <p><span className="text-gray-500">아이디:</span> <span className="font-medium">{user.username}</span></p>
            <p><span className="text-gray-500">역할:</span> <span className="font-medium">{user.role}</span></p>
            <p>
              <span className="text-gray-500">LLM 자격증명:</span>{' '}
              <span className={`font-medium ${hasCreds ? 'text-green-600' : 'text-gray-400'}`}>
                {hasCreds ? '개별 등록됨' : '미등록 (팀 자격증명 사용)'}
              </span>
            </p>
          </div>
        </div>

        {/* LLM 자격증명 */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Key size={16} className="text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-700">개별 LLM 자격증명 (DevX Gateway)</h3>
          </div>
          <p className="text-xs text-gray-500 mb-3">
            개인 client_id / client_secret 발급받았으면 등록하세요. 미등록 시 팀 공용 자격증명(.env)으로 호출됩니다.
          </p>
          <div className="space-y-2">
            <input
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="client_id (예: usr-XXXXXXXXXX)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="client_secret"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <input
              type="text"
              value={llmUserId}
              onChange={(e) => setLlmUserId(e.target.value)}
              placeholder="dify user ID (예: 20251105_xxxxxxxxxx)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <button
              onClick={handleSaveCreds}
              disabled={credSaving || (!clientId && !clientSecret && !llmUserId)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {credSaving ? '저장 중...' : '저장'}
            </button>
          </div>
          {credMsg && <p className={`mt-2 text-sm ${credMsg.includes('실패') ? 'text-red-600' : 'text-green-600'}`}>{credMsg}</p>}
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
