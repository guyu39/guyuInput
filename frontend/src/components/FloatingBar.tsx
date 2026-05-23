import { useAppStore } from '../stores/appStore'
import { useInputStore } from '../stores/inputStore'
import { MinimizeToTray } from '../../wailsjs/go/main/App'

function FloatingBar() {
  const appState = useAppStore((s) => s.appState)
  const inputMode = useAppStore((s) => s.inputMode)
  const volume = useInputStore((s) => s.volume)
  const error = useInputStore((s) => s.error)

  const statusText: Record<string, string> = {
    idle: '待机',
    recording: '录音中',
    recognizing: '识别中',
    inputted: '已输入',
  }

  const stateColor: Record<string, string> = {
    idle: '#60a5fa',
    recording: '#f87171',
    recognizing: '#fbbf24',
    inputted: '#4ade80',
  }

  const modeLabel = inputMode === 'voice' ? '语音' : inputMode === 'keyboard' ? '键盘' : '就绪'
  const modeColor = inputMode === 'voice' ? '#4ade80' : inputMode === 'keyboard' ? '#60a5fa' : '#94a3b8'

  const volumePercent = Math.round(volume * 100)
  const volumeBars = Math.min(Math.round(volume * 10), 10)

  return (
    <div
      className="no-select bg-[#1b2636] rounded-xl px-3 py-1 shadow-lg flex items-center gap-2.5"
      style={{ '--wails-draggable': 'drag' } as React.CSSProperties}
    >
      {/* 左侧：状态指示 */}
      <div className="flex items-center gap-1.5 shrink-0">
        <span
          className="w-2 h-2 rounded-full transition-colors duration-300"
          style={{
            backgroundColor: stateColor[appState],
            boxShadow: `0 0 5px ${stateColor[appState]}80`,
          }}
        />
        <span className="text-slate-200 text-xs font-semibold whitespace-nowrap">
          {statusText[appState]}
        </span>
      </div>

      {/* 分隔 */}
      <span className="text-white/25 font-light text-xs">|</span>

      {/* 中间：输入模式 + 音量条 */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span
          className="text-xs px-1.5 py-0.5 rounded font-medium"
          style={{ backgroundColor: modeColor + '22', color: modeColor }}
        >
          {modeLabel}
        </span>

        {appState === 'recording' && (
          <div className="flex items-center gap-1.5">
            <div className="flex items-end gap-px h-3">
              {Array.from({ length: 10 }).map((_, i) => (
                <div
                  key={i}
                  className="w-0.5 rounded-sm transition-all duration-75"
                  style={{
                    height: `${Math.max(3, (i < volumeBars ? (i + 1) * 10 : 5))}%`,
                    backgroundColor: i < volumeBars ? '#4ade80' : '#334155',
                    boxShadow: i < volumeBars ? '0 0 3px #4ade8080' : undefined,
                  }}
                />
              ))}
            </div>
            <span className="text-slate-400 text-[10px] w-7 tabular-nums">{volumePercent}%</span>
          </div>
        )}

        {appState === 'recognizing' && (
          <div className="flex items-center gap-1.5">
            <span className="flex gap-0.5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1 h-1 rounded-full bg-amber-400 animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </span>
            <span className="text-slate-400 text-[10px]">识别中</span>
          </div>
        )}

        {appState === 'idle' && (
          <span className="text-slate-500 text-[10px]">
            {inputMode === 'voice' ? '快捷键' : '拼音'}输入
          </span>
        )}
      </div>

      {/* 右侧：错误提示 + 最小化按钮 */}
      <div className="flex items-center gap-1 shrink-0">
        {error && (
          <span
            className="text-[10px] text-red-400 max-w-[100px] truncate bg-red-500/10 px-1.5 py-0.5 rounded"
            title={error}
          >
            {error}
          </span>
        )}
        <button
          className="text-slate-500 hover:text-slate-300 hover:bg-white/10 text-sm leading-none px-1 py-0.5 rounded transition-all"
          onClick={() => MinimizeToTray()}
          title="最小化到托盘"
        >
          —
        </button>
      </div>
    </div>
  )
}

export default FloatingBar
