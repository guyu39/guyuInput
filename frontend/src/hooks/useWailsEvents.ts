import { useEffect } from 'react'
import { EventsOn } from '../../wailsjs/runtime/runtime'
import { useAppStore } from '../stores/appStore'
import { useInputStore } from '../stores/inputStore'

export function useWailsEvents() {
  const setAppState = useAppStore((s) => s.setAppState)
  const setInputMode = useAppStore((s) => s.setInputMode)
  const setShowGuide = useAppStore((s) => s.setShowGuide)
  const setShowSettings = useAppStore((s) => s.setShowSettings)
  const setCandidates = useInputStore((s) => s.setCandidates)
  const setASRPartial = useInputStore((s) => s.setASRPartial)
  const setASRFinal = useInputStore((s) => s.setASRFinal)
  const setVolume = useInputStore((s) => s.setVolume)
  const setError = useInputStore((s) => s.setError)

  useEffect(() => {
    const unsubs: (() => void)[] = []

    unsubs.push(
      EventsOn('status-changed', (state: string) => {
        setAppState(state as any)
      })
    )

    unsubs.push(
      EventsOn('input-mode-changed', (mode: string) => {
        setInputMode(mode as any)
      })
    )

    unsubs.push(
      EventsOn('candidates', (result: any) => {
        setCandidates(result)
      })
    )

    unsubs.push(
      EventsOn('asr-partial', (text: string) => {
        setASRPartial(text)
      })
    )

    unsubs.push(
      EventsOn('asr-final', (text: string) => {
        setASRFinal(text)
      })
    )

    unsubs.push(
      EventsOn('audio-volume', (vol: number) => {
        setVolume(vol)
      })
    )

    unsubs.push(
      EventsOn('app-error', (msg: string) => {
        setError(msg)
        setTimeout(() => setError(null), 5000)
      })
    )

    unsubs.push(
      EventsOn('show-guide', (_: boolean) => {
        setShowGuide(true)
      })
    )

    unsubs.push(
      EventsOn('show-settings', (_: boolean) => {
        setShowSettings(true)
      })
    )

    return () => {
      unsubs.forEach((fn) => fn())
    }
  }, [])
}
