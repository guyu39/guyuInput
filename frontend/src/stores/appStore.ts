import { create } from 'zustand'

export type AppState = 'idle' | 'recording' | 'recognizing' | 'inputted'
export type InputMode = 'voice' | 'keyboard' | 'idle'

interface AppStore {
  // 应用状态
  appState: AppState
  inputMode: InputMode
  asrMode: string
  showGuide: boolean
  showSettings: boolean
  isMuted: boolean

  // Actions
  setAppState: (state: AppState) => void
  setInputMode: (mode: InputMode) => void
  setASRMode: (mode: string) => void
  setShowGuide: (show: boolean) => void
  setShowSettings: (show: boolean) => void
  setMuted: (muted: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  appState: 'idle',
  inputMode: 'idle',
  asrMode: 'auto',
  showGuide: false,
  showSettings: false,
  isMuted: false,

  setAppState: (appState) => set({ appState }),
  setInputMode: (inputMode) => set({ inputMode }),
  setASRMode: (asrMode) => set({ asrMode }),
  setShowGuide: (showGuide) => set({ showGuide }),
  setShowSettings: (showSettings) => set({ showSettings }),
  setMuted: (isMuted) => set({ isMuted }),
}))
