import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { GetConfig, SetConfig, GetAllConfig, ResetConfig, GetAudioDevices, SetAudioDevice, ImportDict, GetDictStats } from '../../wailsjs/go/main/App'

interface Props {
  onClose: () => void
}

function SettingsPanel({ onClose }: Props) {
  const asrMode = useAppStore((s) => s.asrMode)
  const setASRMode = useAppStore((s) => s.setASRMode)

  const [audioDevices, setAudioDevices] = useState<{ id: string; name: string; is_default: boolean }[]>([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [candidateCount, setCandidateCount] = useState('5')
  const [dictStats, setDictStats] = useState({ system_word_count: 0, user_word_count: 0, custom_word_count: 0, total_lookups: 0 })
  const [importPath, setImportPath] = useState('')

  useEffect(() => {
    loadSettings()
    loadAudioDevices()
    loadDictStats()
  }, [])

  const loadSettings = async () => {
    const count = await GetConfig('candidate_count')
    setCandidateCount(count || '5')
  }

  const loadAudioDevices = async () => {
    try {
      const devices = await GetAudioDevices()
      setAudioDevices(devices || [])
      const def = (devices || []).find((d) => d.is_default)
      if (def) setSelectedDevice(def.id)
    } catch (_) {}
  }

  const loadDictStats = async () => {
    try {
      const stats = await GetDictStats()
      setDictStats(stats)
    } catch (_) {}
  }

  const handleASRModeChange = async (mode: string) => {
    setASRMode(mode)
    await SetConfig('asr_mode', mode)
  }

  const handleCandidateCountChange = async (count: string) => {
    setCandidateCount(count)
    await SetConfig('candidate_count', count)
  }

  const handleDeviceChange = async (id: string) => {
    setSelectedDevice(id)
    await SetAudioDevice(id)
  }

  const handleImportDict = async () => {
    const path = prompt('请输入词库文件路径（TXT/CSV）:', importPath)
    if (!path) return
    setImportPath(path)
    try {
      const count = await ImportDict(path)
      alert(`成功导入 ${count} 个词条`)
      loadDictStats()
    } catch (e: any) {
      alert(`导入失败: ${e}`)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1b2636] rounded-xl p-6 w-[480px] max-h-[80vh] overflow-y-auto border border-white/10 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">设置</h2>
          <button className="text-[#94a3b8] hover:text-white" onClick={onClose}>✕</button>
        </div>

        {/* ASR 模式 */}
        <div className="mb-4">
          <label className="text-sm text-[#94a3b8] block mb-2">语音识别模式</label>
          <div className="flex gap-2">
            {[
              { value: 'auto', label: '自动切换' },
              { value: 'online', label: '仅在线' },
              { value: 'offline', label: '仅离线' },
            ].map((opt) => (
              <button
                key={opt.value}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  asrMode === opt.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-white/5 text-[#94a3b8] hover:bg-white/10'
                }`}
                onClick={() => handleASRModeChange(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 候选词数量 */}
        <div className="mb-4">
          <label className="text-sm text-[#94a3b8] block mb-2">候选词数量</label>
          <select
            className="bg-white/5 text-white px-3 py-1.5 rounded-lg text-sm border border-white/10"
            value={candidateCount}
            onChange={(e) => handleCandidateCountChange(e.target.value)}
          >
            {['3', '5', '7', '9'].map((n) => (
              <option key={n} value={n}>{n} 个</option>
            ))}
          </select>
        </div>

        {/* 音频设备 */}
        <div className="mb-4">
          <label className="text-sm text-[#94a3b8] block mb-2">麦克风设备</label>
          <select
            className="bg-white/5 text-white px-3 py-1.5 rounded-lg text-sm border border-white/10 w-full"
            value={selectedDevice}
            onChange={(e) => handleDeviceChange(e.target.value)}
          >
            {audioDevices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} {d.is_default ? '(默认)' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* 词库管理 */}
        <div className="mb-4">
          <label className="text-sm text-[#94a3b8] block mb-2">词库管理</label>
          <div className="flex gap-2 mb-2">
            <button
              className="px-3 py-1.5 rounded-lg text-sm bg-white/5 text-[#94a3b8] hover:bg-white/10 transition-colors"
              onClick={handleImportDict}
            >
              导入词库
            </button>
          </div>
          <div className="text-xs text-[#64748b]">
            系统词库: {dictStats.system_word_count} | 用户词库: {dictStats.user_word_count} | 自定义: {dictStats.custom_word_count}
          </div>
        </div>

        {/* 恢复默认 */}
        <div className="pt-4 border-t border-white/10">
          <button
            className="px-3 py-1.5 rounded-lg text-sm bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
            onClick={async () => {
              await ResetConfig()
              loadSettings()
            }}
          >
            恢复默认设置
          </button>
        </div>
      </div>
    </div>
  )
}

export default SettingsPanel
