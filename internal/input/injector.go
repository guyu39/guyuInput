package input

import (
	"syscall"
	"unicode/utf8"
	"unsafe"
)

// InjectMethod 注入方式
type InjectMethod string

const (
	InjectAuto      InjectMethod = "auto"
	InjectSendInput InjectMethod = "send_input"
	InjectClipboard InjectMethod = "clipboard"
)

// Injector 文本注入器
type Injector struct {
	method InjectMethod
}

// NewInjector 创建注入器
func NewInjector() *Injector {
	return &Injector{method: InjectAuto}
}

// Inject 注入文本到当前光标位置
func (inj *Injector) Inject(text string) error {
	if utf8.RuneCountInString(text) < 50 {
		return inj.injectBySendInput(text)
	}
	return inj.injectByClipboard(text)
}

// InjectWithMethod 指定注入方式
func (inj *Injector) InjectWithMethod(text string, method InjectMethod) error {
	switch method {
	case InjectSendInput:
		return inj.injectBySendInput(text)
	case InjectClipboard:
		return inj.injectByClipboard(text)
	default:
		return inj.Inject(text)
	}
}

// injectBySendInput 通过 SendInput API 逐字符注入
func (inj *Injector) injectBySendInput(text string) error {
	user32 := syscall.NewLazyDLL("user32.dll")
	procSendInput := user32.NewProc("SendInput")

	type keyboardInput struct {
		wVk         uint16
		wScan       uint16
		dwFlags     uint32
		time        uint32
		dwExtraInfo uintptr
	}

	type input struct {
		inputType uint32
		ki        keyboardInput
		_         [8]byte // padding
	}

	const (
		inputKeyboard    = 1
		keyEventFUnicode = 0x0004
		keyEventFKeyUp   = 0x0002
	)

	for _, r := range text {
		inputs := [2]input{
			{
				inputType: inputKeyboard,
				ki: keyboardInput{
					wScan:   uint16(r),
					dwFlags: keyEventFUnicode,
				},
			},
			{
				inputType: inputKeyboard,
				ki: keyboardInput{
					wScan:   uint16(r),
					dwFlags: keyEventFUnicode | keyEventFKeyUp,
				},
			},
		}
		procSendInput.Call(
			2,
			uintptr(unsafe.Pointer(&inputs[0])),
			uintptr(unsafe.Sizeof(input{})),
		)
	}
	return nil
}

// injectByClipboard 通过剪贴板 + Ctrl+V 注入
func (inj *Injector) injectByClipboard(text string) error {
	if err := setClipboard(text); err != nil {
		return err
	}
	return inj.simulateCtrlV()
}

// SimulateKeyCombo 模拟组合键
func (inj *Injector) SimulateKeyCombo(modifier uint16, key uint16) error {
	user32 := syscall.NewLazyDLL("user32.dll")
	procKeybdEvent := user32.NewProc("keybd_event")

	const keyEventFKeyUp = 0x0002

	// 按下修饰键
	procKeybdEvent.Call(uintptr(modifier), 0, 0, 0)
	// 按下目标键
	procKeybdEvent.Call(uintptr(key), 0, 0, 0)
	// 释放目标键
	procKeybdEvent.Call(uintptr(key), 0, keyEventFKeyUp, 0)
	// 释放修饰键
	procKeybdEvent.Call(uintptr(modifier), 0, keyEventFKeyUp, 0)

	return nil
}

func (inj *Injector) simulateCtrlV() error {
	const (
		vkControl = 0x11
		vkV       = 0x56
	)
	return inj.SimulateKeyCombo(vkControl, vkV)
}

// setClipboard 设置剪贴板文本
func setClipboard(text string) error {
	user32 := syscall.NewLazyDLL("user32.dll")
	kernel32 := syscall.NewLazyDLL("kernel32.dll")

	procOpenClipboard := user32.NewProc("OpenClipboard")
	procEmptyClipboard := user32.NewProc("EmptyClipboard")
	procSetClipboardData := user32.NewProc("SetClipboardData")
	procCloseClipboard := user32.NewProc("CloseClipboard")
	procGlobalAlloc := kernel32.NewProc("GlobalAlloc")
	procGlobalLock := kernel32.NewProc("GlobalLock")
	procGlobalUnlock := kernel32.NewProc("GlobalUnlock")

	const (
		gmemMoveable = 0x0002
		cfUnicodeText = 13
	)

	ret, _, _ := procOpenClipboard.Call(0)
	if ret == 0 {
		return syscall.GetLastError()
	}
	defer procCloseClipboard.Call()

	procEmptyClipboard.Call()

	utf16, _ := syscall.UTF16FromString(text)
	size := len(utf16) * 2

	hMem, _, _ := procGlobalAlloc.Call(gmemMoveable, uintptr(size))
	if hMem == 0 {
		return syscall.GetLastError()
	}

	pMem, _, _ := procGlobalLock.Call(hMem)
	if pMem == 0 {
		return syscall.GetLastError()
	}

	for i, v := range utf16 {
		*(*uint16)(unsafe.Pointer(pMem + uintptr(i*2))) = v
	}

	procGlobalUnlock.Call(hMem)
	procSetClipboardData.Call(cfUnicodeText, hMem)

	return nil
}
