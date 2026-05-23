package hotkey

import (
	"fmt"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"unsafe"
)

const (
	ModAlt   = 0x0001
	ModCtrl  = 0x0002
	ModShift = 0x0004
	ModWin   = 0x0008

	whKeyboardLl  = 13
	wmKeyDown     = 0x0100
	wmSysKeyDown  = 0x0104
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

// Manager 全局快捷键管理器（WH_KEYBOARD_LL 方案）
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
// WH_KEYBOARD_LL 要求安装钩子的线程有消息循环，因此放在独立 goroutine 中并 LockOSThread
func (m *Manager) Start() error {
	m.stopChan = make(chan struct{})
	errCh := make(chan error, 1)

	go func() {
		runtime.LockOSThread()
		defer runtime.UnlockOSThread()

		user32 := syscall.NewLazyDLL("user32.dll")
		kernel32 := syscall.NewLazyDLL("kernel32.dll")

		procSetWindowsHookEx := user32.NewProc("SetWindowsHookExW")
		procGetModuleHandle := kernel32.NewProc("GetModuleHandleW")
		procGetMessage := user32.NewProc("GetMessageW")
		procTranslateMessage := user32.NewProc("TranslateMessage")
		procDispatchMessage := user32.NewProc("DispatchMessageW")
		procUnhookWindowsHookEx := user32.NewProc("UnhookWindowsHookEx")

		hMod, _, _ := procGetModuleHandle.Call(0)

		hook, _, hookErr := procSetWindowsHookEx.Call(
			whKeyboardLl,
			syscall.NewCallback(m.keyboardProc),
			hMod,
			0,
		)
		if hook == 0 {
			errCh <- fmt.Errorf("注册键盘钩子失败: %v", hookErr)
			return
		}

		m.mu.Lock()
		m.hook = hook
		m.mu.Unlock()

		errCh <- nil

		// 消息泵：WH_KEYBOARD_LL 事件通过线程消息队列投递
		type msg struct {
			hwnd    uintptr
			message uint32
			wParam  uintptr
			lParam  uintptr
			time    uint32
			ptX     int32
			ptY     int32
		}

		for {
			select {
			case <-m.stopChan:
				procUnhookWindowsHookEx.Call(hook)
				m.mu.Lock()
				m.hook = 0
				m.mu.Unlock()
				// 排空残余消息
				procPostQuitMessage := user32.NewProc("PostQuitMessage")
				procPostQuitMessage.Call(0)
				return
			default:
			}

			var ms msg
			ret, _, _ := procGetMessage.Call(uintptr(unsafe.Pointer(&ms)), 0, 0, 0, 1) // PM_REMOVE
			if ret == 0 || ret == ^uintptr(0) {
				return
			}
			procTranslateMessage.Call(uintptr(unsafe.Pointer(&ms)))
			procDispatchMessage.Call(uintptr(unsafe.Pointer(&ms)))
		}
	}()

	return <-errCh
}

// keyboardProc 键盘钩子回调
func (m *Manager) keyboardProc(nCode int32, wParam uintptr, lParam uintptr) uintptr {
	if nCode >= 0 {
		type kbdllhookstruct struct {
			vkCode      uint32
			scanCode    uint32
			flags       uint32
			time        uint32
			dwExtraInfo uintptr
		}

		kbd := (*kbdllhookstruct)(unsafe.Pointer(lParam))

		isKeyDown := wParam == wmKeyDown || wParam == wmSysKeyDown
		vk := uint16(kbd.vkCode)

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
	m.mu.Lock()
	hasHook := m.hook != 0
	m.mu.Unlock()
	if hasHook {
		close(m.stopChan)
	}
}

// RegisterCtrlAltV 注册 Ctrl+Alt+V（按下录音，松开停止）
func (m *Manager) RegisterCtrlAltV(onPress, onRelease Callback) error {
	const vkV = 0x56
	return m.Register("voice-record", ModCtrl|ModAlt, vkV, onPress, onRelease)
}

// ParseHotkeyString 解析快捷键字符串 "ctrl+alt+v" 返回 modifiers 和 vkCode
func ParseHotkeyString(s string) (modifiers uint16, vkCode uint16, err error) {
	parts := strings.Split(strings.ToLower(s), "+")
	var mods uint16
	var key string

	for _, p := range parts {
		p = strings.TrimSpace(p)
		switch p {
		case "ctrl":
			mods |= ModCtrl
		case "alt":
			mods |= ModAlt
		case "shift":
			mods |= ModShift
		case "win":
			mods |= ModWin
		default:
			key = p
		}
	}

	if key == "" {
		return 0, 0, fmt.Errorf("快捷键缺少按键: %s", s)
	}

	vk, ok := keyToVK(key)
	if !ok {
		return 0, 0, fmt.Errorf("不支持的按键: %s", key)
	}

	return mods, vk, nil
}

func keyToVK(key string) (uint16, bool) {
	if len(key) == 1 && key[0] >= 'a' && key[0] <= 'z' {
		return uint16(key[0] - 'a' + 0x41), true
	}
	if len(key) == 1 && key[0] >= '0' && key[0] <= '9' {
		return uint16(key[0]), true
	}
	fkMap := map[string]uint16{
		"f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
		"f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
		"f9": 0x78, "f10": 0x79, "f11": 0x7a, "f12": 0x7b,
		"space": 0x20, "tab": 0x09, "enter": 0x0d,
	}
	vk, ok := fkMap[key]
	return vk, ok
}

// ReregisterVoiceHotkey 重新注册语音快捷键
func (m *Manager) ReregisterVoiceHotkey(hotkeyStr string, onPress, onRelease Callback) error {
	m.Unregister("voice-record")
	mods, vk, err := ParseHotkeyString(hotkeyStr)
	if err != nil {
		return err
	}
	return m.Register("voice-record", mods, vk, onPress, onRelease)
}
