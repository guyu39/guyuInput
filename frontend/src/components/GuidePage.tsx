import { useState } from 'react'
import { CompleteGuide } from '../../wailsjs/go/main/App'

interface Props {
  onComplete: () => void
}

const steps = [
  {
    title: '欢迎使用 guyuInput',
    desc: '智能输入法，支持语音和键盘两种输入方式，自由切换。',
    icon: '🎤',
  },
  {
    title: '语音输入',
    desc: '按住 Ctrl+Alt+V 开始录音，松开自动识别并输入到当前光标位置。',
    icon: '🎙️',
  },
  {
    title: '键盘输入',
    desc: '直接打字即可使用拼音输入。候选词出现后，按 1-5 数字键选词，空格选首词。',
    icon: '⌨️',
  },
  {
    title: '试试看',
    desc: '打开记事本或任何文本输入框，试试语音或键盘输入吧！',
    icon: '✨',
  },
]

function GuidePage({ onComplete }: Props) {
  const [step, setStep] = useState(0)

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1)
    } else {
      CompleteGuide()
      onComplete()
    }
  }

  return (
    <div className="fixed inset-0 bg-[#0f172a] flex items-center justify-center z-50">
      <div className="text-center max-w-sm px-6">
        {/* 图标 */}
        <div className="text-5xl mb-6">{steps[step].icon}</div>

        {/* 进度指示器 */}
        <div className="flex justify-center gap-1.5 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`h-1 rounded-full transition-all duration-300 ${
                i === step ? 'w-8 bg-blue-500' : i < step ? 'w-4 bg-blue-500/50' : 'w-4 bg-white/10'
              }`}
            />
          ))}
        </div>

        {/* 内容 */}
        <h1 className="text-xl font-semibold text-white mb-3">{steps[step].title}</h1>
        <p className="text-[#94a3b8] text-sm leading-relaxed mb-8">{steps[step].desc}</p>

        {/* 按钮 */}
        <div className="flex gap-3 justify-center">
          <button
            className="px-6 py-2.5 rounded-xl bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
            onClick={handleNext}
          >
            {step < steps.length - 1 ? '下一步' : '开始使用'}
          </button>
        </div>

        {/* 跳过 */}
        {step < steps.length - 1 && (
          <button
            className="mt-4 text-xs text-[#64748b] hover:text-[#94a3b8] transition-colors"
            onClick={() => {
              CompleteGuide()
              onComplete()
            }}
          >
            跳过引导
          </button>
        )}
      </div>
    </div>
  )
}

export default GuidePage
