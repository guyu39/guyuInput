import { useInputStore } from '../stores/inputStore'
import { useAppStore } from '../stores/appStore'
import { SelectCandidate, CommitCandidate, ClearPinyinBuf, ProcessKey } from '../../wailsjs/go/main/App'

function CandidateWindow() {
  const pinyin = useInputStore((s) => s.pinyin)
  const candidates = useInputStore((s) => s.candidates)
  const inputMode = useAppStore((s) => s.inputMode)

  if (inputMode !== 'keyboard' || !pinyin) {
    return null
  }

  const handleSelect = (index: number) => {
    SelectCandidate(index + 1)
  }

  const handleBackspace = () => {
    ProcessKey('\b')
  }

  const handleClear = () => {
    ClearPinyinBuf()
  }

  return (
    <div className="no-select bg-[#1b2636]/95 backdrop-blur rounded-lg px-3 py-2 min-w-[200px] border border-white/10 shadow-lg">
      {/* 拼音显示 */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[#94a3b8] text-sm">{pinyin || ' '}</span>
        <button
          className="text-[#94a3b8] hover:text-white text-xs px-1"
          onClick={handleClear}
        >
          ✕
        </button>
      </div>

      {/* 候选词列表 */}
      {candidates.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {candidates.map((word, i) => (
            <button
              key={i}
              className={`text-sm px-2 py-0.5 rounded transition-colors ${
                i === 0
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-[#e2e8f0] hover:bg-white/10'
              }`}
              onClick={() => handleSelect(i)}
            >
              <span className="text-xs text-[#94a3b8] mr-1">{i + 1}</span>
              {word}
            </button>
          ))}
        </div>
      ) : (
        <span className="text-[#94a3b8] text-xs">无匹配结果</span>
      )}
    </div>
  )
}

export default CandidateWindow
