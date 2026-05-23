package main

import (
	"embed"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/linux"
	"github.com/wailsapp/wails/v2/pkg/options/mac"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	app := NewApp()

	err := wails.Run(&options.App{
		Title:     "guyuInput",
		Width:     320,
		Height:    200,
		MinWidth:  280,
		MinHeight: 100,

		// 无边框 + 透明背景
		Frameless:        true,
		AlwaysOnTop:      true,
		BackgroundColour: &options.RGBA{R: 0, G: 0, B: 0, A: 0},
		DisableResize:    true,

		// 不在任务栏显示（悬浮窗形态）
		Windows: &windows.Options{
			WebviewIsTransparent: true,
			WindowIsTranslucent:  true,
		},
		Mac: &mac.Options{
			TitleBar:             mac.TitleBarHiddenInset(),
			WebviewIsTransparent: true,
			WindowIsTranslucent:  true,
		},
		Linux: &linux.Options{
			WindowIsTranslucent: true,
		},

		AssetServer: &assetserver.Options{
			Assets: assets,
		},

		OnStartup:  app.startup,
		OnShutdown: app.shutdown,
		OnDomReady: app.domReady,

		Bind: []interface{}{app},
	})

	if err != nil {
		println("Error:", err.Error())
	}
}
