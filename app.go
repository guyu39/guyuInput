package main

import (
	"context"

	"guyuInput/internal/audio"
	"guyuInput/internal/asr"
	"guyuInput/internal/config"
	"guyuInput/internal/dict"
	"guyuInput/internal/hotkey"
	"guyuInput/internal/input"
	"guyuInput/internal/logger"
	"guyuInput/internal/pinyin"
	"guyuInput/internal/storage"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App 主应用结构体（Wails Bind 方法注册在此）
type App struct {
	ctx        context.Context
	audioCap   audio.Capture
	asrDisp    *asr.Dispatcher
	pinyinEng  *pinyin.Engine
	injector   *input.Injector
	dispatcher *input.Dispatcher
	configMgr  *config.Manager
	hotkeyMgr  *hotkey.Manager
	dictMgr    *dict.Manager
}

// NewApp 创建 App 实例
func NewApp() *App {
	return &App{}
}

// startup Wails 生命周期：应用启动时调用
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx

	logger.Init()
	logger.Info("应用启动")

	// 初始化数据库
	if err := storage.Init(); err != nil {
		logger.Errorf("数据库初始化失败: %v", err)
	}

	// 初始化各模块
	a.audioCap = audio.NewCapture()
	a.injector = input.NewInjector()
	a.configMgr = config.NewManager()
	a.configMgr.Load()

	a.dictMgr = dict.NewManager()
	a.pinyinEng = pinyin.NewEngine(a.dictMgr)
	a.hotkeyMgr = hotkey.NewManager()

	// 在线 ASR（讯飞）
	onlineASR := asr.NewXunfeiClient()

	// 离线 ASR（MVP 阶段暂不实装，V2.0）
	a.asrDisp = asr.NewDispatcher(onlineASR, nil, asr.ModeAuto)

	// 输入模式调度器
	a.dispatcher = input.NewDispatcher(a.audioCap, a.asrDisp, a.pinyinEng, a.injector)

	// 设置事件回调（Go → 前端推送）
	a.dispatcher.SetCallbacks(
		func(mode input.InputMode) {
			runtime.EventsEmit(a.ctx, "input-mode-changed", string(mode))
		},
		func(state input.AppState) {
			runtime.EventsEmit(a.ctx, "status-changed", string(state))
		},
		func(result *pinyin.CandidateResult) {
			runtime.EventsEmit(a.ctx, "candidates", result)
		},
		func(vol float32) {
			runtime.EventsEmit(a.ctx, "audio-volume", vol)
		},
		func(text, resultType string) {
			runtime.EventsEmit(a.ctx, "asr-"+resultType, text)
		},
		func(errMsg string) {
			runtime.EventsEmit(a.ctx, "app-error", errMsg)
		},
	)

	// 注册全局快捷键
	a.hotkeyMgr.RegisterCtrlAltV(
		func() { // 按下 → 开始录音
			logger.Info("快捷键按下: 开始录音")
			a.dispatcher.StartVoice()
		},
		func() { // 松开 → 停止录音
			logger.Info("快捷键松开: 停止录音")
			a.dispatcher.StopVoice()
		},
	)

	// 启动键盘钩子
	if err := a.hotkeyMgr.Start(); err != nil {
		logger.Errorf("键盘钩子启动失败: %v", err)
	}

	// 如果不是首次运行，直接显示悬浮窗
	if !a.configMgr.GetBool("first_run") {
		runtime.WindowShow(a.ctx)
	}

	logger.Info("应用启动完成")
}

// shutdown Wails 生命周期：应用关闭时调用
func (a *App) shutdown(ctx context.Context) {
	logger.Info("应用关闭")
	a.hotkeyMgr.Stop()
	a.asrDisp.Close()
	storage.Close()
}

// domReady Wails 生命周期：前端 DOM 就绪
func (a *App) domReady(ctx context.Context) {
	// 首次运行显示引导页
	if a.configMgr.GetBool("first_run") {
		runtime.EventsEmit(a.ctx, "show-guide", true)
	}
}

// ===================== 录音控制 =====================

// StartRecording 开始录音
func (a *App) StartRecording() {
	a.dispatcher.StartVoice()
}

// StopRecording 停止录音
func (a *App) StopRecording() {
	a.dispatcher.StopVoice()
}

// CancelRecording 取消本次录音
func (a *App) CancelRecording() {
	a.audioCap.Stop()
}

// IsRecording 是否正在录音
func (a *App) IsRecording() bool {
	return a.audioCap.IsRecording()
}

// GetVolume 获取当前音量
func (a *App) GetVolume() float32 {
	return a.audioCap.Volume()
}

// ===================== 识别相关 =====================

// GetASRMode 获取 ASR 模式
func (a *App) GetASRMode() string {
	return string(a.asrDisp.Mode())
}

// SetASRMode 设置 ASR 模式
func (a *App) SetASRMode(mode string) {
	a.asrDisp.SetMode(asr.ASRMode(mode))
}

// ===================== 键盘输入 =====================

// ProcessKey 处理按键事件（由前端调用）
func (a *App) ProcessKey(key string) *pinyin.CandidateResult {
	if len(key) == 0 {
		return nil
	}
	runes := []rune(key)
	return a.dispatcher.OnKeyPress(runes[0])
}

// SelectCandidate 选择候选词 (index: 1-5)
func (a *App) SelectCandidate(index int) string {
	result := a.pinyinEng.ProcessKey(rune('0' + index))
	if result != nil {
		return result.Committed
	}
	return ""
}

// CommitCandidate 直接提交指定文字
func (a *App) CommitCandidate(text string) {
	a.injector.Inject(text)
	a.pinyinEng.ClearBuf()
}

// ClearPinyinBuf 清空拼音缓冲区
func (a *App) ClearPinyinBuf() {
	a.pinyinEng.ClearBuf()
}

// GetPinyinBuf 获取当前拼音
func (a *App) GetPinyinBuf() string {
	return a.pinyinEng.GetPinyinBuf()
}

// GetInputMode 获取当前输入模式
func (a *App) GetInputMode() string {
	return string(a.dispatcher.GetCurrentMode())
}

// GetAppState 获取应用状态
func (a *App) GetAppState() string {
	return string(a.dispatcher.GetAppState())
}

// ===================== 配置管理 =====================

// GetConfig 获取配置项
func (a *App) GetConfig(key string) string {
	return a.configMgr.Get(key)
}

// SetConfig 设置配置项
func (a *App) SetConfig(key, value string) error {
	return a.configMgr.Set(key, value)
}

// GetAllConfig 获取全部配置（JSON）
func (a *App) GetAllConfig() string {
	return a.configMgr.GetAllJSON()
}

// ResetConfig 恢复默认配置
func (a *App) ResetConfig() error {
	return a.configMgr.Reset()
}

// ===================== 词库管理 =====================

// ImportDict 导入词库文件
func (a *App) ImportDict(filePath string) (int, error) {
	return a.dictMgr.ImportFile(filePath)
}

// GetDictStats 获取词库统计
func (a *App) GetDictStats() dict.Stats {
	return a.dictMgr.Stats()
}

// AddCustomWord 添加自定义词
func (a *App) AddCustomWord(word, pinyin string, freq int) error {
	return a.dictMgr.AddWord(word, pinyin, freq)
}

// ===================== 音频设备 =====================

// GetAudioDevices 获取可用音频设备
func (a *App) GetAudioDevices() []audio.Device {
	devices, _ := a.audioCap.ListDevices()
	return devices
}

// SetAudioDevice 选择音频设备
func (a *App) SetAudioDevice(id string) error {
	return a.audioCap.SelectDevice(id)
}

// ===================== 应用控制 =====================

// MinimizeToTray 最小化到托盘
func (a *App) MinimizeToTray() {
	runtime.WindowHide(a.ctx)
}

// ShowWindow 显示窗口
func (a *App) ShowWindow() {
	runtime.WindowShow(a.ctx)
}

// GetVersion 获取版本号
func (a *App) GetVersion() string {
	return "0.1.0"
}

// CompleteGuide 完成引导
func (a *App) CompleteGuide() {
	a.configMgr.Set("first_run", "false")
}

// CheckFirstRun 检查是否首次运行
func (a *App) CheckFirstRun() bool {
	return a.configMgr.GetBool("first_run")
}
