import { useState } from 'react'
import { useAppStore } from './stores/appStore'
import { useWailsEvents } from './hooks/useWailsEvents'
import FloatingBar from './components/FloatingBar'
import CandidateWindow from './components/CandidateWindow'
import SettingsPanel from './components/SettingsPanel'
import GuidePage from './components/GuidePage'
import { MinimizeToTray } from '../wailsjs/go/main/App'

function App() {
  const [showSettings, setShowSettings] = useState(false)
  const showGuide = useAppStore((s) => s.showGuide)

  // 注册所有 Wails 事件监听
  useWailsEvents()

  return (
    <div id="App" className="h-screen bg-transparent">
      {/* 主悬浮窗 + 候选词 */}
      <div className="flex flex-col gap-1 p-2">
        <FloatingBar />
        <CandidateWindow />
      </div>

      {/* 底部按钮组 */}
      <div className="flex justify-center gap-2 mt-1 px-2">
        <button
          className="text-[#64748b] hover:text-white text-xs px-2 py-1 rounded transition-colors"
          onClick={() => setShowSettings(true)}
        >
          设置
        </button>
        <button
          className="text-[#64748b] hover:text-white text-xs px-2 py-1 rounded transition-colors"
          onClick={() => MinimizeToTray()}
        >
          最小化
        </button>
      </div>

      {/* 设置面板（模态） */}
      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}

      {/* 首次使用引导 */}
      {showGuide && (
        <GuidePage onComplete={() => useAppStore.getState().setShowGuide(false)} />
      )}
    </div>
  )
}

export default App
