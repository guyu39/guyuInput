import { useState, useEffect, useCallback, useRef } from 'react'
import { useAppStore } from '../stores/appStore'
import { useToastStore } from './Toast'
import {
  GetConfig, SetConfig, ResetConfig,
  GetAudioDevices, SetAudioDevice,
  ImportDict, GetDictStats,
  GetHotkey, SetHotkey,
} from '../../wailsjs/go/main/App'

interface Props {
  onClose: () => void
}

// 多供应商 API 字段定义
interface ProviderDef {
  key: string
  name: string
  fields: { id: string; label: string; secret?: boolean }[]
}

const PROVIDERS: ProviderDef[] = [
  {
    key: 'xunfei',
    name: '讯飞',
    fields: [
      { id: 'app_id', label: 'App ID' },
      { id: 'api_key', label: 'API Key' },
      { id: 'api_secret', label: 'API Secret', secret: true },
    ],
  },
  {
    key: 'doubao',
    name: '豆包',
    fields: [
      { id: 'app_id', label: 'App ID' },
      { id: 'access_token', label: 'Access Token', secret: true },
    ],
  },
  {
    key: 'alibaba',
    name: '阿里',
    fields: [
      { id: 'access_key_id', label: 'AccessKey ID' },
      { id: 'access_key_secret', label: 'AccessKey Secret', secret: true },
      { id: 'app_key', label: 'App Key' },
    ],
  },
  {
    key: 'minimax',
    name: 'MiniMax',
    fields: [
      { id: 'api_key', label: 'API Key', secret: true },
      { id: 'group_id', label: 'Group ID' },
    ],
  },
]

function SettingsPanel({ onClose }: Props) {
  const asrMode = useAppStore((s) => s.asrMode)
  const setASRMode = useAppStore((s) => s.setASRMode)
  const toast = useToastStore((s) => s.show)

  const [audioDevices, setAudioDevices] = useState<{ id: string; name: string; is_default: boolean }[]>([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [dictStats, setDictStats] = useState({ system_word_count: 0, user_word_count: 0, custom_word_count: 0, total_lookups: 0 })

  // 快捷键
  const [hotkey, setHotkey] = useState('ctrl+alt+v')
  const [recording, setRecording] = useState(false)
  const hotkeyRef = useRef(hotkey)
  hotkeyRef.current = hotkey

  // 多供应商 API
  const [asrProvider, setAsrProvider] = useState('xunfei')
  const [credsValues, setCredsValues] = useState<Record<string, string>>({})
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})

  const currentProvider = PROVIDERS.find((p) => p.key === asrProvider) || PROVIDERS[0]

  // 导入词库路径
  const [importPath, setImportPath] = useState('')

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    try {
      const provider = await GetConfig('asr_provider')
      if (provider) setAsrProvider(provider)
    } catch (_) {}

    // 加载所有供应商的凭证
    const allValues: Record<string, string> = {}
    for (const p of PROVIDERS) {
      for (const f of p.fields) {
        try {
          const key = `asr_${p.key}_${f.id}`
          const val = await GetConfig(key)
          if (val) allValues[key] = val
        } catch (_) {}
      }
    }
    setCredsValues(allValues)

    try {
      const hk = await GetHotkey()
      if (hk) setHotkey(hk)
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

  // 获取当前供应商的凭证值
  const getCredValue = (fieldId: string) => {
    const key = `asr_${asrProvider}_${fieldId}`
    return credsValues[key] || ''
  }

  const setCredValue = (fieldId: string, value: string) => {
    const key = `asr_${asrProvider}_${fieldId}`
    setCredsValues((prev) => ({ ...prev, [key]: value }))
  }

  // 当前供应商是否已配置（所有字段非空）
  const hasProviderCreds = currentProvider.fields.every((f) => !!getCredValue(f.id))

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

  const handleProviderChange = async (key: string) => {
    setAsrProvider(key)
    await SetConfig('asr_provider', key)
  }

  const handleDeviceChange = async (id: string) => {
    setSelectedDevice(id)
    await SetAudioDevice(id)
  }

  const handleSaveCredentials = async () => {
    try {
      for (const f of currentProvider.fields) {
        const key = `asr_${asrProvider}_${f.id}`
        await SetConfig(key, getCredValue(f.id))
      }
      toast(`${currentProvider.name} API 凭证已保存`, 'success')
    } catch (e: any) {
      toast('保存失败: ' + e, 'error')
    }
  }

  const toggleSecret = (fieldId: string) => {
    setShowSecrets((prev) => ({ ...prev, [fieldId]: !prev[fieldId] }))
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

          {/* === API 凭证（多供应商）=== */}
          <Section title="语音 API 凭证">
            {/* 供应商选择 */}
            <div className="flex gap-1.5 mb-3 flex-wrap">
              {PROVIDERS.map((p) => (
                <button
                  key={p.key}
                  className={`px-3 py-1 rounded-lg text-xs transition-colors ${
                    asrProvider === p.key
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : 'bg-white/5 text-[#94a3b8] border border-transparent hover:bg-white/10'
                  }`}
                  onClick={() => handleProviderChange(p.key)}
                >
                  {p.name}
                </button>
              ))}
            </div>

            {/* 配置状态指示 */}
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-2 h-2 rounded-full ${hasProviderCreds ? 'bg-green-500' : 'bg-[#64748b]'}`} />
              <span className="text-xs text-[#94a3b8]">
                {currentProvider.name} — {hasProviderCreds ? '已配置' : '未配置'}
              </span>
            </div>

            {/* 凭证字段 */}
            <div className="space-y-2">
              {currentProvider.fields.map((f) => {
                const isSecret = f.secret && !showSecrets[f.id]
                return (
                  <div key={f.id} className="flex gap-1 items-end">
                    <div className="flex-1">
                      <InputField
                        label={f.label}
                        value={getCredValue(f.id)}
                        onChange={(v) => setCredValue(f.id, v)}
                        type={isSecret ? 'password' : 'text'}
                      />
                    </div>
                    {f.secret && (
                      <button
                        className="text-xs text-[#64748b] hover:text-[#94a3b8] pb-1.5 shrink-0"
                        onClick={() => toggleSecret(f.id)}
                      >
                        {isSecret ? '显示' : '隐藏'}
                      </button>
                    )}
                  </div>
                )
              })}
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

          {/* === 麦克风设备 === */}
          <Section title="麦克风设备">
            <DeviceSelect
              devices={audioDevices}
              selectedId={selectedDevice}
              onChange={handleDeviceChange}
            />
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

/** 设备下拉选择 */
function DeviceSelect({ devices, selectedId, onChange }: {
  devices: { id: string; name: string; is_default: boolean }[]
  selectedId: string
  onChange: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const selected = devices.find((d) => d.id === selectedId)
  const displayName = selected
    ? `${selected.name}${selected.is_default ? ' (默认)' : ''}`
    : '选择设备'

  return (
    <div ref={ref} className="relative">
      <button
        className="w-full bg-white/5 text-white text-xs px-3 py-1.5 rounded-lg border border-white/10 flex items-center justify-between gap-2 hover:border-white/20 transition-colors text-left"
        onClick={() => setOpen(!open)}
      >
        <span className="truncate">{displayName}</span>
        <svg className={`w-3 h-3 shrink-0 text-[#94a3b8] transition-transform ${open ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-[#1e293b] border border-white/10 rounded-lg shadow-xl z-50 max-h-[180px] overflow-y-auto settings-scroll">
          {devices.length === 0 ? (
            <div className="px-3 py-2 text-xs text-[#64748b]">未检测到设备</div>
          ) : (
            devices.map((d) => (
              <button
                key={d.id}
                className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                  d.id === selectedId
                    ? 'bg-blue-500/15 text-blue-400'
                    : 'text-[#e2e8f0] hover:bg-white/5'
                }`}
                onClick={() => { onChange(d.id); setOpen(false) }}
              >
                {d.name}
                {d.is_default && <span className="text-[#64748b] ml-1">(默认)</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default SettingsPanel
