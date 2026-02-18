import { create } from 'zustand';

const useWindowStore = create((set, get) => ({
  showCadWindow: false,
  showBrowserWindow: false,
  showKasaWindow: false,
  showPrinterWindow: false,
  showSettings: false,
  showTerminal: false,
  showScheduler: false,
  showAlerts: false,
  showPluginManager: false,
  showModelSettings: false,
  showMemoryViewer: false,
  showIntegrations: false,
  showMessaging: false,
  showFileBrowser: false,

  isModularMode: false,

  elementPositions: {
    video: { x: 40, y: 80 },
    visualizer: { x: window.innerWidth / 2, y: window.innerHeight / 2 - 150 },
    chat: { x: window.innerWidth / 2, y: window.innerHeight / 2 + 100 },
    cad: { x: window.innerWidth / 2 + 300, y: window.innerHeight / 2 },
    browser: { x: window.innerWidth / 2 - 300, y: window.innerHeight / 2 },
    kasa: { x: window.innerWidth / 2 + 350, y: window.innerHeight / 2 - 100 },
    printer: { x: window.innerWidth / 2 - 350, y: window.innerHeight / 2 - 100 },
    tools: { x: window.innerWidth / 2, y: window.innerHeight - 100 },
    terminal: { x: window.innerWidth / 2, y: window.innerHeight / 2 },
    scheduler: { x: window.innerWidth / 2 + 200, y: window.innerHeight / 2 },
    alerts: { x: window.innerWidth / 2 - 200, y: window.innerHeight / 2 },
  },

  elementSizes: {
    visualizer: { w: 550, h: 350 },
    chat: { w: 550, h: 220 },
    tools: { w: 500, h: 80 },
    cad: { w: 400, h: 400 },
    browser: { w: 550, h: 380 },
    video: { w: 320, h: 180 },
    kasa: { w: 300, h: 380 },
    printer: { w: 380, h: 380 },
    terminal: { w: 600, h: 400 },
    scheduler: { w: 400, h: 350 },
    alerts: { w: 400, h: 350 },
  },

  zIndexOrder: ['visualizer', 'chat', 'tools', 'video', 'cad', 'browser', 'kasa', 'printer', 'terminal', 'scheduler', 'alerts'],
  activeDragElement: null,

  toggleWindow: (name) => set((state) => ({ [name]: !state[name] })),
  setWindow: (name, visible) => set({ [name]: visible }),
  setIsModularMode: (mode) => set({ isModularMode: mode }),
  setElementPosition: (id, pos) => set((state) => ({
    elementPositions: { ...state.elementPositions, [id]: pos }
  })),
  setElementSize: (id, size) => set((state) => ({
    elementSizes: { ...state.elementSizes, [id]: size }
  })),
  bringToFront: (id) => set((state) => ({
    zIndexOrder: [...state.zIndexOrder.filter(z => z !== id), id]
  })),
  setActiveDragElement: (el) => set({ activeDragElement: el }),
}));

export default useWindowStore;
