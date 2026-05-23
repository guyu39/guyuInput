import { useEffect, useState } from 'react'
import { create } from 'zustand'

interface ToastState {
  message: string | null
  type: 'success' | 'error' | 'info'
  show: (message: string, type?: 'success' | 'error' | 'info') => void
  hide: () => void
}

export const useToastStore = create<ToastState>((set) => ({
  message: null,
  type: 'info',
  show: (message, type = 'info') => set({ message, type }),
  hide: () => set({ message: null }),
}))

function Toast() {
  const message = useToastStore((s) => s.message)
  const type = useToastStore((s) => s.type)
  const hide = useToastStore((s) => s.hide)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (message) {
      setVisible(true)
      const t = setTimeout(() => {
        setVisible(false)
        setTimeout(hide, 300)
      }, 2500)
      return () => clearTimeout(t)
    }
  }, [message, hide])

  if (!message) return null

  const colorMap = {
    success: 'border-green-500/50 bg-green-500/10 text-green-400',
    error: 'border-red-500/50 bg-red-500/10 text-red-400',
    info: 'border-blue-500/50 bg-blue-500/10 text-blue-400',
  }

  return (
    <div
      className={`fixed top-3 left-1/2 -translate-x-1/2 z-[100] px-4 py-2 rounded-lg border text-sm transition-all duration-300 ${
        colorMap[type]
      } ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'}`}
    >
      {message}
    </div>
  )
}

export default Toast
