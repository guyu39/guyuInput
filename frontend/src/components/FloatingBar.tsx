import { useAppStore } from '../stores/appStore'
import { useInputStore } from '../stores/inputStore'

function FloatingBar() {
  const appState = useAppStore((s) => s.appState)
  const inputMode = useAppStore((s) => s.inputMode)
  const asrMode = useAppStore((s) => s.asrMode)
  const volume = useInputStore((s) => s.volume)
  const error = useInputStore((s) => s.error)

  const statusText: Record<string, string> = {
    idle: '待机',
    recording: '录音中',
    recognizing: '识别中',
    inputted: '已输入',
  }

  const stateColor: Record<string, string> = {
    idle: '#94a3b8',
    recording: '#ef4444',
    recognizing: '#f59e0b',
    inputted: '#22c55e',
  }

  const modeLabel = inputMode === 'voice' ? '语音' : inputMode === 'keyboard' ? '键盘' : '--'
  const modeColor = inputMode === 'voice' ? '#22c55e' : inputMode === 'keyboard' ? '#3b82f6' : '#94a3b8'

  const volumePercent = Math.round(volume * 100)
  const volumeBars = Math.min(Math.round(volume * 10), 10)

  return (
    <div
      className="no-select bg-[#1b2636]/90 backdrop-blur rounded-xl px-4 py-2 min-w-[280px] border border-white/10 shadow-lg"
      style={{ '--wails-draggable': 'drag' } as React.CSSProperties}
    >
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-white text-sm font-medium">guyuInput</span>
        <div className="flex items-center gap-2">
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ backgroundColor: modeColor + '20', color: modeColor }}
          >
            {modeLabel}
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ backgroundColor: stateColor[appState] + '20', color: stateColor[appState] }}
          >
            {statusText[appState]}
          </span>
        </div>
      </div>

      {/* 音量指示器 */}
      {appState === 'recording' && (
        <div className="flex items-center gap-1.5 mb-1">
          <div className="flex items-end gap-0.5 h-3">
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className="w-1 rounded-sm transition-all duration-100"
                style={{
                  height: `${Math.max(2, (i < volumeBars ? (i + 1) * 10 : 0))}%`,
                  backgroundColor: i < volumeBars ? '#22c55e' : '#334155',
                  minHeight: 2,
                }}
              />
            ))}
          </div>
          <span className="text-[#94a3b8] text-xs">{volumePercent}%</span>
        </div>
      )}

      {/* ASR 模式指示 */}
      <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
        <span>在线 <span style={{ color: asrMode === 'offline' ? '#94a3b8' : '#22c55e' }}>●</span></span>
        <span>离线 <span style={{ color: asrMode === 'offline' ? '#22c55e' : '#94a3b8' }}>○</span></span>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mt-1.5 text-xs text-red-400 bg-red-400/10 px-2 py-1 rounded">
          {error}
        </div>
      )}
    </div>
  )
}

export default FloatingBar
