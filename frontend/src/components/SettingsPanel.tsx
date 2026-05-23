import { useState, useEffect, useCallback, useRef } from 'react'
import { useAppStore } from '../stores/appStore'
import { useToastStore } from './Toast'
import {
  GetConfig, SetConfig, ResetConfig,
  GetAudioDevices, SetAudioDevice,
  ImportDict, GetDictStats,
  GetHotkey, SetHotkey,
  GetXunfeiCredentials, SetXunfeiCredentials, HasXunfeiCredentials,
} from '../../wailsjs/go/main/App'

interface Props {
  onClose: () => void
}

function SettingsPanel({ onClose }: Props) {
  const asrMode = useAppStore((s) => s.asrMode)
  const setASRMode = useAppStore((s) => s.setASRMode)
  const toast = useToastStore((s) => s.show)

  const [audioDevices, setAudioDevices] = useState<{ id: string; name: string; is_default: boolean }[]>([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [candidateCount, setCandidateCount] = useState('5')
  const [dictStats, setDictStats] = useState({ system_word_count: 0, user_word_count: 0, custom_word_count: 0, total_lookups: 0 })

  // 快捷键
  const [hotkey, setHotkey] = useState('ctrl+alt+v')
  const [recording, setRecording] = useState(false)
  const hotkeyRef = useRef(hotkey)
  hotkeyRef.current = hotkey

  // API 凭证
  const [appID, setAppID] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [hasCreds, setHasCreds] = useState(false)
  const [showSecret, setShowSecret] = useState(false)

  // 导入词库路径
  const [importPath, setImportPath] = useState('')

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    try {
      const count = await GetConfig('candidate_count')
      setCandidateCount(count || '5')
    } catch (_) {}
    try {
      const hk = await GetHotkey()
      if (hk) setHotkey(hk)
    } catch (_) {}
    try {
      const creds = await GetXunfeiCredentials()
      setAppID(creds.app_id || '')
      setApiKey(creds.api_key || '')
      setHasCreds(await HasXunfeiCredentials())
    } catch (_) {}
    try {
      const devices = await GetAudioDevices()
      setAudioDevices(devices || [])
      const def = (devices || []).find((d) => d.is_default)
      if (def) setSelectedDevice(def.id)
    } catch (_) {}
    try {
      const stats = await GetDictStats()
      setDictStats(stats)
    } catch (_) {}
  }

  // ===== 快捷键录制 =====
  const handleHotkeyRecord = useCallback(() => {
    setRecording(true)
  }, [])

  useEffect(() => {
    if (!recording) return

    const onKeyDown = (e: KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()

      const parts: string[] = []
      if (e.ctrlKey) parts.push('ctrl')
      if (e.altKey) parts.push('alt')
      if (e.shiftKey) parts.push('shift')
      if (e.metaKey) parts.push('win')

      // 忽略纯修饰键
      const key = e.key.toLowerCase()
      if (['control', 'alt', 'shift', 'meta'].includes(key)) return

      if (key === ' ') {
        parts.push('space')
      } else if (key.length === 1 || key.startsWith('f')) {
        parts.push(key)
      } else {
        return
      }

      const combo = parts.join('+')
      setHotkey(combo)
      setRecording(false)
      SetHotkey(combo).then(() => {
        toast('快捷键已更新: ' + combo, 'success')
      }).catch((err: any) => {
        toast('快捷键无效: ' + err, 'error')
      })
    }

    window.addEventListener('keydown', onKeyDown, true)
    return () => window.removeEventListener('keydown', onKeyDown, true)
  }, [recording, toast])

  // ===== 其他处理 =====
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

  const handleSaveCredentials = async () => {
    try {
      await SetXunfeiCredentials(appID, apiKey, apiSecret)
      setHasCreds(!!appID && !!apiKey && !!apiSecret)
      toast('API 凭证已保存', 'success')
    } catch (e: any) {
      toast('保存失败: ' + e, 'error')
    }
  }

  const handleImportDict = async () => {
    if (!importPath) return
    try {
      const count = await ImportDict(importPath)
      toast(`成功导入 ${count} 个词条`, 'success')
      setImportPath('')
      const stats = await GetDictStats()
      setDictStats(stats)
    } catch (e: any) {
      toast(`导入失败: ${e}`, 'error')
    }
  }

  const handleReset = async () => {
    await ResetConfig()
    await loadAll()
    toast('已恢复默认设置', 'info')
  }

  return (
    <div className="absolute inset-0 bg-[#1b2636] overflow-y-auto px-5 pt-5 pb-3 settings-scroll z-50">
        {/* 标题 */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">设置</h2>
          <button className="text-[#94a3b8] hover:text-white text-lg leading-none" onClick={onClose}>✕</button>
        </div>

          {/* === 语音识别模式 === */}
          <Section title="识别模式">
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
          </Section>

          {/* === API 凭证 === */}
          <Section title="讯飞 API 凭证">
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-2 h-2 rounded-full ${hasCreds ? 'bg-green-500' : 'bg-[#64748b]'}`} />
              <span className="text-xs text-[#94a3b8]">{hasCreds ? '已配置' : '未配置'}</span>
            </div>
            <div className="space-y-2">
              <InputField label="App ID" value={appID} onChange={setAppID} />
              <InputField label="API Key" value={apiKey} onChange={setApiKey} />
              <div className="flex gap-1 items-end">
                <div className="flex-1">
                  <InputField
                    label="API Secret"
                    value={apiSecret}
                    onChange={setApiSecret}
                    type={showSecret ? 'text' : 'password'}
                  />
                </div>
                <button
                  className="text-xs text-[#64748b] hover:text-[#94a3b8] pb-1.5"
                  onClick={() => setShowSecret(!showSecret)}
                >
                  {showSecret ? '隐藏' : '显示'}
                </button>
              </div>
            </div>
            <button
              className="mt-2 px-3 py-1 rounded-lg text-xs bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-colors"
              onClick={handleSaveCredentials}
            >
              保存凭证
            </button>
          </Section>

          {/* === 快捷键 === */}
          <Section title="录音快捷键">
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white font-mono text-center">
                {recording ? '按下组合键...' : hotkey}
              </div>
              <button
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  recording
                    ? 'bg-red-500/20 text-red-400 animate-pulse'
                    : 'bg-white/5 text-[#94a3b8] hover:bg-white/10'
                }`}
                onClick={handleHotkeyRecord}
              >
                {recording ? '录制中' : '录制'}
              </button>
            </div>
          </Section>

          {/* === 候选词数量 === */}
          <Section title="候选词数量">
            <div className="flex gap-2">
              {['3', '5', '7', '9'].map((n) => (
                <button
                  key={n}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    candidateCount === n
                      ? 'bg-blue-500 text-white'
                      : 'bg-white/5 text-[#94a3b8] hover:bg-white/10'
                  }`}
                  onClick={() => handleCandidateCountChange(n)}
                >
                  {n} 个
                </button>
              ))}
            </div>
          </Section>

          {/* === 麦克风设备 === */}
          <Section title="麦克风设备">
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
          </Section>

          {/* === 词库管理 === */}
          <Section title="词库管理">
            <div className="flex gap-2 mb-2">
              <input
                className="flex-1 bg-white/5 text-white text-xs px-3 py-1.5 rounded-lg border border-white/10 outline-none focus:border-blue-500/50"
                placeholder="输入词库文件路径 (TXT/CSV)"
                value={importPath}
                onChange={(e) => setImportPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleImportDict()}
              />
              <button
                className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-[#94a3b8] hover:bg-white/10 transition-colors"
                onClick={handleImportDict}
              >
                导入
              </button>
            </div>
            <div className="text-xs text-[#64748b]">
              系统词库: {dictStats.system_word_count} | 用户词库: {dictStats.user_word_count} | 自定义: {dictStats.custom_word_count}
            </div>
          </Section>

          {/* === 恢复默认 === */}
          <div className="pt-4 border-t border-white/10">
            <button
              className="px-3 py-1.5 rounded-lg text-xs bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
              onClick={handleReset}
            >
              恢复默认设置
            </button>
          </div>
    </div>
  )
}

/** 区块标题 */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <label className="text-sm text-[#94a3b8] block mb-2">{title}</label>
      {children}
    </div>
  )
}

/** 输入框 */
function InputField({ label, value, onChange, type = 'text' }: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
}) {
  return (
    <input
      type={type}
      className="w-full bg-white/5 text-white text-xs px-3 py-1.5 rounded-lg border border-white/10 outline-none focus:border-blue-500/50"
      placeholder={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

export default SettingsPanel
