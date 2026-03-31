import { useEffect, useRef } from 'react';

export function useAutoRefresh(callback: () => void, intervalMs: number = 15000) {
  const cb = useRef(callback);
  cb.current = callback;

  useEffect(() => {
    // 주기적 polling
    const timer = setInterval(() => cb.current(), intervalMs);

    // 탭 포커스 시 즉시 리로드
    const onFocus = () => cb.current();
    window.addEventListener('focus', onFocus);

    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', onFocus);
    };
  }, [intervalMs]);
}
