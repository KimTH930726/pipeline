import { useEffect, useRef } from 'react';

export function useWebSocket(url: string | null, onMessage: (data: unknown) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!url) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        onMessage(event.data);
      }
    };

    ws.onerror = () => {
      console.error('WebSocket error');
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [url]);

  return wsRef;
}
