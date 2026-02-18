import { create } from 'zustand';

const useMediaStore = create((set) => ({
  isMuted: true,
  isVideoOn: false,
  aiAudioData: new Array(64).fill(0),
  micAudioData: new Array(32).fill(0),
  fps: 0,

  micDevices: [],
  speakerDevices: [],
  webcamDevices: [],
  selectedMicId: localStorage.getItem('selectedMicId') || '',
  selectedSpeakerId: localStorage.getItem('selectedSpeakerId') || '',
  selectedWebcamId: localStorage.getItem('selectedWebcamId') || '',

  setIsMuted: (muted) => set({ isMuted: muted }),
  setIsVideoOn: (on) => set({ isVideoOn: on }),
  setAiAudioData: (data) => set({ aiAudioData: data }),
  setMicAudioData: (data) => set({ micAudioData: data }),
  setFps: (fps) => set({ fps }),
  setMicDevices: (devices) => set({ micDevices: devices }),
  setSpeakerDevices: (devices) => set({ speakerDevices: devices }),
  setWebcamDevices: (devices) => set({ webcamDevices: devices }),
  setSelectedMicId: (id) => { localStorage.setItem('selectedMicId', id); set({ selectedMicId: id }); },
  setSelectedSpeakerId: (id) => { localStorage.setItem('selectedSpeakerId', id); set({ selectedSpeakerId: id }); },
  setSelectedWebcamId: (id) => { localStorage.setItem('selectedWebcamId', id); set({ selectedWebcamId: id }); },
}));

export default useMediaStore;
