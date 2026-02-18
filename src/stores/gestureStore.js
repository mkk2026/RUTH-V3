import { create } from 'zustand';

const useGestureStore = create((set) => ({
  cursorPos: { x: 0, y: 0 },
  isPinching: false,
  isHandTrackingEnabled: false,
  cursorSensitivity: 2.0,
  isCameraFlipped: false,
  ripples: [],

  setCursorPos: (pos) => set({ cursorPos: pos }),
  setIsPinching: (pinching) => set({ isPinching: pinching }),
  setIsHandTrackingEnabled: (enabled) => set({ isHandTrackingEnabled: enabled }),
  setCursorSensitivity: (sensitivity) => set({ cursorSensitivity: sensitivity }),
  setIsCameraFlipped: (flipped) => set({ isCameraFlipped: flipped }),
  addRipple: (ripple) => set((state) => ({ ripples: [...state.ripples, ripple] })),
  removeRipple: (id) => set((state) => ({ ripples: state.ripples.filter(r => r.id !== id) })),
}));

export default useGestureStore;
