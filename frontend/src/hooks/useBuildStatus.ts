import { useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { useDeployStore } from '../store/deployStore';
import type { BuildLogMessage, RCAReport } from '../types/deploy';

export function useBuildStatus(deploymentId: number | null) {
  const { addLogLine, setRCA, setBuildStatus } = useDeployStore();

  const wsUrl = deploymentId
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/deploy/ws/${deploymentId}`
    : null;

  const handleMessage = useCallback((data: unknown) => {
    const msg = data as BuildLogMessage;
    if (msg.type === 'log_line') {
      addLogLine(msg.data as string);
    } else if (msg.type === 'status') {
      setBuildStatus(msg.data as string);
    } else if (msg.type === 'rca') {
      setRCA(msg.data as RCAReport);
    }
  }, [addLogLine, setRCA, setBuildStatus]);

  useWebSocket(wsUrl, handleMessage);
}
