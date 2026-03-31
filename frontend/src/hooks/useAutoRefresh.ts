import { useEffect, useRef } from 'react';

export function useAutoRefresh(callback: () => void) {
  const cb = useRef(callback);
  cb.current = callback;

  useEffect(() => {
    const onFocus = () => cb.current();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, []);
}
