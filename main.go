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
		Width:     280,
		Height:    36,
		MinWidth:  100,
		MinHeight: 36,

		// 无边框悬浮窗，背景色与内层控件统一 (#1b2636)
		Frameless:        true,
		AlwaysOnTop:      true,
		DisableResize:    true,
		BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},

		Windows: &windows.Options{
			WebviewIsTransparent: true,
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
