//go:build !windows

package systray

// Init 初始化系统托盘（非 Windows 平台空实现）
func Init(iconPath string, showFn, settingsFn, quitFn func()) error {
	return nil
}

// Quit 退出托盘（非 Windows 平台空实现）
func Quit() {}
