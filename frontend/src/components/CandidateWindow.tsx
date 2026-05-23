import { useEffect, useState } from 'react'
import { useInputStore } from '../stores/inputStore'
import { useAppStore } from '../stores/appStore'
import { SelectCandidate, ClearPinyinBuf } from '../../wailsjs/go/main/App'

function CandidateWindow() {
  const pinyin = useInputStore((s) => s.pinyin)
  const candidates = useInputStore((s) => s.candidates)
  const inputMode = useAppStore((s) => s.inputMode)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (inputMode === 'keyboard' && pinyin) {
      setVisible(true)
    } else {
      setVisible(false)
    }
  }, [inputMode, pinyin])

  if (inputMode !== 'keyboard' || !pinyin) {
    return null
  }

  const handleSelect = (index: number) => {
    SelectCandidate(index + 1)
  }

  return (
    <div
      className={`no-select bg-[#1b2636] rounded-lg px-2.5 py-1 shadow-lg flex items-center gap-1.5 transition-all duration-150 ${
        visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
      }`}
    >
      {/* 拼音 + 闪烁光标 */}
      <span className="text-slate-300 text-xs flex items-center gap-px">
        {pinyin}
        <span className="w-px h-3 bg-blue-400 animate-pulse ml-0.5" />
      </span>

      <span className="text-white/25 text-xs font-light">|</span>

      {candidates.length > 0 ? (
        <div className="flex gap-0.5">
          {candidates.map((word, i) => (
            <button
              key={i}
              className={`text-xs px-1.5 py-0.5 rounded transition-all active:scale-95 ${
                i === 0
                  ? 'bg-blue-500/25 text-blue-300 hover:bg-blue-500/40'
                  : 'text-slate-200 hover:bg-white/10'
              }`}
              onClick={() => handleSelect(i)}
            >
              <span className="text-[10px] text-blue-400/70 mr-0.5">{i + 1}</span>
              {word}
            </button>
          ))}
        </div>
      ) : (
        <span className="text-slate-500 text-xs">无匹配</span>
      )}

      <button
        className="text-slate-500 hover:text-slate-300 hover:bg-white/10 text-xs ml-1 px-1 py-0.5 rounded transition-all"
        onClick={() => ClearPinyinBuf()}
      >
        ✕
      </button>
    </div>
  )
}

export default CandidateWindow
