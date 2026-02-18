import { create } from 'zustand';

const useConnectionStore = create((set) => ({
  status: 'Disconnected',
  socketConnected: false,
  isConnected: true,
  isAuthenticated: false,
  isLockScreenVisible: false,
  faceAuthEnabled: false,
  currentProject: 'default',

  setStatus: (status) => set({ status }),
  setSocketConnected: (connected) => set({ socketConnected: connected }),
  setIsConnected: (connected) => set({ isConnected: connected }),
  setIsAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),
  setIsLockScreenVisible: (visible) => set({ isLockScreenVisible: visible }),
  setFaceAuthEnabled: (enabled) => set({ faceAuthEnabled: enabled }),
  setCurrentProject: (project) => set({ currentProject: project }),
}));

export default useConnectionStore;
