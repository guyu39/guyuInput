//go:build windows

package systray

import (
	"runtime"
	"syscall"
	"unsafe"
)

const (
	nimAdd         = 0x00000000
	nimModify      = 0x00000001
	nimDelete      = 0x00000002
	nimSetVersion  = 0x00000004
	nifMessage     = 0x00000001
	nifIcon        = 0x00000002
	nifTip         = 0x00000004
	nifState       = 0x00000008
	nifInfo        = 0x00000010
	nifGuid        = 0x00000020
	wmApp          = 0x8000
	wmTrayIcon     = wmApp + 1
	wmLButtonUp    = 0x0202
	wmRButtonUp    = 0x0205
	wmCommand      = 0x0111
	idiApplication = 32512

	// 托盘菜单 ID
	menuSettings = 1001
	menuQuit     = 1002
)

type guid struct {
	Data1 uint32
	Data2 uint16
	Data3 uint16
	Data4 [8]byte
}

type notifyIconData struct {
	cbSize           uint32
	hWnd             uintptr
	uID              uint32
	uFlags           uint32
	uCallbackMessage uint32
	hIcon            uintptr
	szTip            [128]uint16
	dwState          uint32
	dwStateMask      uint32
	szInfo           [256]uint16
	uTimeout         uint32
	szInfoTitle      [64]uint16
	dwInfoFlags      uint32
	guidItem         guid
	hBalloonIcon     uintptr
}

type msg struct {
	hwnd    uintptr
	message uint32
	wParam  uintptr
	lParam  uintptr
	time    uint32
	ptX     int32
	ptY     int32
}

type point struct {
	x int32
	y int32
}

var (
	onShow  func()
	onQuit  func()
	onSettings func()

	user32  = syscall.NewLazyDLL("user32.dll")
	shell32 = syscall.NewLazyDLL("shell32.dll")

	procShellNotifyIcon  = shell32.NewProc("Shell_NotifyIconW")
	procDefWindowProc    = user32.NewProc("DefWindowProcW")
	procGetModuleHandle  = syscall.NewLazyDLL("kernel32.dll").NewProc("GetModuleHandleW")
	procLoadIcon         = user32.NewProc("LoadIconW")
	procCreateWindowEx   = user32.NewProc("CreateWindowExW")
	procPostQuitMessage  = user32.NewProc("PostQuitMessage")
	procGetMessage       = user32.NewProc("GetMessageW")
	procTranslateMessage = user32.NewProc("TranslateMessage")
	procDispatchMessage  = user32.NewProc("DispatchMessageW")
	procRegisterClassEx  = user32.NewProc("RegisterClassExW")
	procDestroyWindow    = user32.NewProc("DestroyWindow")
	procExtractIcon      = shell32.NewProc("ExtractIconW")

	// 弹出菜单
	procCreatePopupMenu   = user32.NewProc("CreatePopupMenu")
	procAppendMenuW       = user32.NewProc("AppendMenuW")
	procTrackPopupMenu    = user32.NewProc("TrackPopupMenu")
	procDestroyMenu       = user32.NewProc("DestroyMenu")
	procGetCursorPos      = user32.NewProc("GetCursorPos")
	procSetForegroundWindow = user32.NewProc("SetForegroundWindow")

	trayWindow uintptr
)

// Init 初始化系统托盘
func Init(iconPath string, showFn, settingsFn, quitFn func()) error {
	onShow = showFn
	onSettings = settingsFn
	onQuit = quitFn

	icon := loadIconFromFile(iconPath)

	errChan := make(chan error, 1)

	go func() {
		runtime.LockOSThread()
		defer runtime.UnlockOSThread()

		if err := createTrayWindow(); err != nil {
			errChan <- err
			return
		}
		if err := addTrayIcon(icon); err != nil {
			errChan <- err
			return
		}
		errChan <- nil

		for {
			var m msg
			ret, _, _ := procGetMessage.Call(
				uintptr(unsafe.Pointer(&m)), 0, 0, 0,
			)
			if ret == 0 || ret == ^uintptr(0) {
				break
			}
			procTranslateMessage.Call(uintptr(unsafe.Pointer(&m)))
			procDispatchMessage.Call(uintptr(unsafe.Pointer(&m)))
		}

		removeTrayIcon()
		procDestroyWindow.Call(trayWindow)
	}()

	return <-errChan
}

// Quit 退出托盘
func Quit() {
	procPostQuitMessage.Call(0)
}

func createTrayWindow() error {
	hInst, _, _ := procGetModuleHandle.Call(0)

	className := "guyuInputTrayClass"
	classNameUTF16, _ := syscall.UTF16PtrFromString(className)

	type wndClassEx struct {
		cbSize        uint32
		style         uint32
		lpfnWndProc   uintptr
		cbClsExtra    int32
		cbWndExtra    int32
		hInstance     uintptr
		hIcon         uintptr
		hCursor       uintptr
		hbrBackground uintptr
		lpszMenuName  *uint16
		lpszClassName *uint16
		hIconSm       uintptr
	}

	wc := wndClassEx{
		cbSize:        uint32(unsafe.Sizeof(wndClassEx{})),
		lpfnWndProc:   syscall.NewCallback(wndProc),
		hInstance:     hInst,
		lpszClassName: classNameUTF16,
	}

	procRegisterClassEx.Call(uintptr(unsafe.Pointer(&wc)))

	trayWindow, _, _ = procCreateWindowEx.Call(
		0,
		uintptr(unsafe.Pointer(classNameUTF16)),
		uintptr(unsafe.Pointer(syscall.StringToUTF16Ptr("TrayWindow"))),
		0,
		0, 0, 0, 0,
		0, 0, hInst, 0,
	)

	if trayWindow == 0 {
		return syscall.GetLastError()
	}

	return nil
}

func addTrayIcon(icon uintptr) error {
	nid := notifyIconData{
		cbSize:           uint32(unsafe.Sizeof(notifyIconData{})),
		hWnd:             trayWindow,
		uID:              1,
		uFlags:           nifMessage | nifIcon | nifTip,
		uCallbackMessage: wmTrayIcon,
		hIcon:            icon,
	}
	copy(nid.szTip[:], syscall.StringToUTF16("guyuInput - 智能输入法"))

	ret, _, _ := procShellNotifyIcon.Call(nimAdd, uintptr(unsafe.Pointer(&nid)))
	if ret == 0 {
		return syscall.GetLastError()
	}

	nid2 := notifyIconData{
		cbSize: uint32(unsafe.Sizeof(notifyIconData{})),
		hWnd:   trayWindow,
		uID:    1,
	}
	procShellNotifyIcon.Call(nimSetVersion, uintptr(unsafe.Pointer(&nid2)))
	return nil
}

func removeTrayIcon() {
	nid := notifyIconData{
		cbSize: uint32(unsafe.Sizeof(notifyIconData{})),
		hWnd:   trayWindow,
		uID:    1,
	}
	procShellNotifyIcon.Call(nimDelete, uintptr(unsafe.Pointer(&nid)))
}

func loadIconFromFile(path string) uintptr {
	if path != "" {
		pathUTF16, _ := syscall.UTF16PtrFromString(path)
		icon, _, _ := procExtractIcon.Call(0, uintptr(unsafe.Pointer(pathUTF16)), 0)
		if icon != 0 {
			return icon
		}
	}
	icon, _, _ := procLoadIcon.Call(0, uintptr(idiApplication))
	return icon
}

func showTrayMenu() {
	menu, _, _ := procCreatePopupMenu.Call()

	settingsPtr, _ := syscall.UTF16PtrFromString("设置")
	procAppendMenuW.Call(menu, 0, uintptr(menuSettings), uintptr(unsafe.Pointer(settingsPtr)))

	procAppendMenuW.Call(menu, 0x800, 0, 0) // MF_SEPARATOR

	quitPtr, _ := syscall.UTF16PtrFromString("退出")
	procAppendMenuW.Call(menu, 0, uintptr(menuQuit), uintptr(unsafe.Pointer(quitPtr)))

	var pt point
	procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))

	// SetForegroundWindow 必须调用，否则菜单点击外部不会消失
	procSetForegroundWindow.Call(trayWindow)

	procTrackPopupMenu.Call(menu, 0, uintptr(pt.x), uintptr(pt.y), 0, trayWindow, 0)

	procDestroyMenu.Call(menu)
}

func wndProc(hwnd uintptr, msg uint32, wParam, lParam uintptr) uintptr {
	switch msg {
	case wmTrayIcon:
		switch lParam {
		case wmLButtonUp:
			if onShow != nil {
				onShow()
			}
		case wmRButtonUp:
			showTrayMenu()
		}
	case wmCommand:
		switch wParam {
		case menuSettings:
			if onSettings != nil {
				onSettings()
			}
		case menuQuit:
			if onQuit != nil {
				onQuit()
			}
		}
	}

	ret, _, _ := procDefWindowProc.Call(hwnd, uintptr(msg), wParam, lParam)
	return ret
}
