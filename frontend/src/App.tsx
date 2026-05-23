import { useAppStore } from './stores/appStore'
import { useWailsEvents } from './hooks/useWailsEvents'
import FloatingBar from './components/FloatingBar'
import CandidateWindow from './components/CandidateWindow'
import SettingsPanel from './components/SettingsPanel'
import GuidePage from './components/GuidePage'
import Toast from './components/Toast'
import { CloseSettings } from '../wailsjs/go/main/App'

function App() {
  const showSettings = useAppStore((s) => s.showSettings)
  const setShowSettings = useAppStore((s) => s.setShowSettings)
  const showGuide = useAppStore((s) => s.showGuide)

  useWailsEvents()

  const handleCloseSettings = () => {
    setShowSettings(false)
    CloseSettings()
  }

  return (
    <div id="App" className="h-screen flex flex-col items-center justify-center gap-0.5">
      <FloatingBar />
      <CandidateWindow />

      {showSettings && (
        <SettingsPanel onClose={handleCloseSettings} />
      )}

      {showGuide && (
        <GuidePage onComplete={() => useAppStore.getState().setShowGuide(false)} />
      )}

      <Toast />
    </div>
  )
}

export default App
