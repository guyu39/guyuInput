package hotkey

import (
	"fmt"
	"sync"
	"syscall"
	"unsafe"
)

const (
	ModAlt   = 0x0001
	ModCtrl  = 0x0002
	ModShift = 0x0004
	ModWin   = 0x0008

	wmHotkey    = 0x0312
	whKeyboardLl = 13
	wmKeyDown    = 0x0100
	wmSysKeyDown = 0x0104
)

// Callback 热键回调
type Callback func()

type hotkeyEntry struct {
	id        string
	modifiers uint16
	vkCode    uint16
	onPress   Callback
	onRelease Callback
	pressed   bool
}

// Manager 全局快捷键管理器（底层键盘钩子方案）
type Manager struct {
	mu       sync.Mutex
	hotkeys  map[string]*hotkeyEntry
	hook     uintptr
	stopChan chan struct{}
}

// NewManager 创建快捷键管理器
func NewManager() *Manager {
	return &Manager{
		hotkeys:  make(map[string]*hotkeyEntry),
		stopChan: make(chan struct{}),
	}
}

// Register 注册全局快捷键（带按下/松开回调）
func (m *Manager) Register(id string, modifiers uint16, vkCode uint16, onPress, onRelease Callback) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.hotkeys[id]; exists {
		return fmt.Errorf("快捷键 %s 已注册", id)
	}

	m.hotkeys[id] = &hotkeyEntry{
		id:        id,
		modifiers: modifiers,
		vkCode:    vkCode,
		onPress:   onPress,
		onRelease: onRelease,
	}

	return nil
}

// Unregister 注销快捷键
func (m *Manager) Unregister(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.hotkeys, id)
	return nil
}

// UnregisterAll 注销所有快捷键
func (m *Manager) UnregisterAll() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.hotkeys = make(map[string]*hotkeyEntry)
}

// Start 启动键盘钩子
func (m *Manager) Start() error {
	user32 := syscall.NewLazyDLL("user32.dll")
	kernel32 := syscall.NewLazyDLL("kernel32.dll")

	procSetWindowsHookEx := user32.NewProc("SetWindowsHookExW")
	procGetModuleHandle := kernel32.NewProc("GetModuleHandleW")

	// 获取当前模块句柄
	hMod, _, _ := procGetModuleHandle.Call(0)

	// 注册底层键盘钩子
	hook, _, err := procSetWindowsHookEx.Call(
		whKeyboardLl,
		syscall.NewCallback(m.keyboardProc),
		hMod,
		0,
	)
	if hook == 0 {
		return fmt.Errorf("注册键盘钩子失败: %v", err)
	}
	m.hook = hook

	return nil
}

// keyboardProc 键盘钩子回调
func (m *Manager) keyboardProc(nCode int32, wParam uintptr, lParam uintptr) uintptr {
	if nCode >= 0 {
		type kbdllhookstruct struct {
			vkCode    uint32
			scanCode  uint32
			flags     uint32
			time      uint32
			dwExtraInfo uintptr
		}

		kbd := (*kbdllhookstruct)(unsafe.Pointer(lParam))

		isKeyDown := wParam == wmKeyDown || wParam == wmSysKeyDown
		vk := uint16(kbd.vkCode)

		// 获取当前修饰键状态
		mods := getModifierState()

		m.mu.Lock()
		for _, entry := range m.hotkeys {
			if vk == entry.vkCode && mods == entry.modifiers {
				if isKeyDown && !entry.pressed {
					entry.pressed = true
					if entry.onPress != nil {
						entry.onPress()
					}
				} else if !isKeyDown && entry.pressed {
					entry.pressed = false
					if entry.onRelease != nil {
						entry.onRelease()
					}
				}
			}
		}
		m.mu.Unlock()
	}

	user32 := syscall.NewLazyDLL("user32.dll")
	procCallNextHookEx := user32.NewProc("CallNextHookEx")
	ret, _, _ := procCallNextHookEx.Call(0, uintptr(nCode), wParam, lParam)
	return ret
}

func getModifierState() uint16 {
	user32 := syscall.NewLazyDLL("user32.dll")
	procGetAsyncKeyState := user32.NewProc("GetAsyncKeyState")

	var mods uint16

	checkKey := func(vk int, mod uint16) {
		ret, _, _ := procGetAsyncKeyState.Call(uintptr(vk))
		if ret&0x8000 != 0 {
			mods |= mod
		}
	}

	checkKey(0x11, ModCtrl)  // VK_CONTROL
	checkKey(0x12, ModAlt)   // VK_MENU
	checkKey(0x10, ModShift) // VK_SHIFT
	checkKey(0x5B, ModWin)   // VK_LWIN

	return mods
}

// Stop 停止钩子
func (m *Manager) Stop() {
	m.UnregisterAll()
	if m.hook != 0 {
		user32 := syscall.NewLazyDLL("user32.dll")
		procUnhookWindowsHookEx := user32.NewProc("UnhookWindowsHookEx")
		procUnhookWindowsHookEx.Call(m.hook)
		m.hook = 0
	}
}

// RegisterCtrlAltV 注册 Ctrl+Alt+V（按下录音，松开停止）
func (m *Manager) RegisterCtrlAltV(onPress, onRelease Callback) error {
	const vkV = 0x56
	return m.Register("voice-record", ModCtrl|ModAlt, vkV, onPress, onRelease)
}
