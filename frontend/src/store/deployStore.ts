import { create } from 'zustand';
import type { DeployStatus, RCAReport, StageKey, StageStatus, StageInfo } from '../types/deploy';

const INITIAL_STAGES: StageInfo[] = [
  { key: 'CONFLICT_CHECK', label: '충돌 확인', status: 'pending' },
  { key: 'BUILD_VALIDATION', label: '빌드 검증', status: 'pending' },
  { key: 'MERGE', label: 'main 머지', status: 'pending' },
  { key: 'DOCKER_RESTART', label: 'Docker 재기동', status: 'pending' },
];

interface DeployState {
  currentDeployment: DeployStatus | null;
  buildLog: string[];
  rcaReport: RCAReport | null;
  buildStatus: string | null;
  stages: StageInfo[];
  startPipeline: () => void;
  setDeployment: (d: DeployStatus) => void;
  addLogLine: (line: string) => void;
  setRCA: (rca: RCAReport) => void;
  setBuildStatus: (status: string) => void;
  updateStage: (key: StageKey, status: StageStatus, label?: string) => void;
  reset: () => void;
}

export const useDeployStore = create<DeployState>((set) => ({
  currentDeployment: null,
  buildLog: [],
  rcaReport: null,
  buildStatus: null,
  stages: INITIAL_STAGES.map((s) => ({ ...s })),
  startPipeline: () => set({
    buildLog: [], rcaReport: null, buildStatus: 'BUILDING',
    stages: INITIAL_STAGES.map((s) => ({ ...s })),
  }),
  setDeployment: (d) => set({ currentDeployment: d }),
  addLogLine: (line) => set((s) => ({ buildLog: [...s.buildLog, line] })),
  setRCA: (rca) => set({ rcaReport: rca }),
  setBuildStatus: (status) => set({ buildStatus: status }),
  updateStage: (key, status, label?) => set((s) => ({
    stages: s.stages.map((st) => st.key === key ? { ...st, status, ...(label ? { label } : {}) } : st),
  })),
  reset: () => set({
    currentDeployment: null, buildLog: [], rcaReport: null, buildStatus: null,
    stages: INITIAL_STAGES.map((s) => ({ ...s })),
  }),
}));
