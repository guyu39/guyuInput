import { create } from 'zustand'

interface CandidateResult {
  pinyin: string
  candidates: string[]
  committed: string
  is_complete: boolean
}

interface InputStore {
  // 拼音
  pinyin: string
  candidates: string[]
  lastCommitted: string

  // 语音识别
  asrPartial: string
  asrFinal: string

  // 音量
  volume: number

  // 错误
  error: string | null

  // Actions
  setCandidates: (result: CandidateResult) => void
  setASRPartial: (text: string) => void
  setASRFinal: (text: string) => void
  setVolume: (vol: number) => void
  setError: (err: string | null) => void
  clearInput: () => void
}

export const useInputStore = create<InputStore>((set) => ({
  pinyin: '',
  candidates: [],
  lastCommitted: '',

  asrPartial: '',
  asrFinal: '',

  volume: 0,
  error: null,

  setCandidates: (result) =>
    set({
      pinyin: result.pinyin,
      candidates: result.candidates,
      lastCommitted: result.committed || '',
    }),

  setASRPartial: (text) => set({ asrPartial: text }),
  setASRFinal: (text) => set({ asrFinal: text, asrPartial: '' }),
  setVolume: (volume) => set({ volume }),
  setError: (error) => set({ error }),

  clearInput: () =>
    set({
      pinyin: '',
      candidates: [],
      asrPartial: '',
      asrFinal: '',
    }),
}))
