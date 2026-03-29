import { create } from 'zustand';
import type { DeployStatus, RCAReport } from '../types/deploy';

interface DeployState {
  currentDeployment: DeployStatus | null;
  buildLog: string[];
  rcaReport: RCAReport | null;
  buildStatus: string | null;
  setDeployment: (d: DeployStatus) => void;
  addLogLine: (line: string) => void;
  setRCA: (rca: RCAReport) => void;
  setBuildStatus: (status: string) => void;
  reset: () => void;
}

export const useDeployStore = create<DeployState>((set) => ({
  currentDeployment: null,
  buildLog: [],
  rcaReport: null,
  buildStatus: null,
  setDeployment: (d) => set({ currentDeployment: d, buildLog: [], rcaReport: null, buildStatus: 'BUILDING' }),
  addLogLine: (line) => set((s) => ({ buildLog: [...s.buildLog, line] })),
  setRCA: (rca) => set({ rcaReport: rca }),
  setBuildStatus: (status) => set({ buildStatus: status }),
  reset: () => set({ currentDeployment: null, buildLog: [], rcaReport: null, buildStatus: null }),
}));
