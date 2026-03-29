import { useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { triggerRollback } from '../../api/deployApi';

interface Props {
  branch: string;
  onRollback?: (result: unknown) => void;
}

export default function RollbackButton({ branch, onRollback }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleRollback = async () => {
    setLoading(true);
    try {
      const result = await triggerRollback(branch);
      onRollback?.(result);
    } catch (err) {
      console.error('Rollback failed:', err);
    } finally {
      setLoading(false);
      setConfirming(false);
    }
  };

  if (!confirming) {
    return (
      <button
        onClick={() => setConfirming(true)}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
      >
        <RotateCcw size={16} />
        원복 실행
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-red-600 font-medium">정말 원복하시겠습니까?</span>
      <button
        onClick={handleRollback}
        disabled={loading}
        className="px-3 py-1.5 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
      >
        {loading ? '처리 중...' : '확인'}
      </button>
      <button
        onClick={() => setConfirming(false)}
        className="px-3 py-1.5 bg-gray-300 text-gray-700 rounded text-sm hover:bg-gray-400"
      >
        취소
      </button>
    </div>
  );
}
