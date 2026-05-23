package input

import (
	"sync"

	"guyuInput/internal/audio"
	"guyuInput/internal/asr"
	"guyuInput/internal/pinyin"
)

// InputMode 输入模式
type InputMode string

const (
	ModeVoice    InputMode = "voice"
	ModeKeyboard InputMode = "keyboard"
	ModeIdle     InputMode = "idle"
)

// AppState 应用状态（对应悬浮窗状态）
type AppState string

const (
	StateIdle       AppState = "idle"
	StateRecording  AppState = "recording"
	StateRecognizing AppState = "recognizing"
	StateInputted   AppState = "inputted"
)

// Dispatcher 输入模式调度器
type Dispatcher struct {
	mu          sync.Mutex
	currentMode InputMode
	appState    AppState

	audio   audio.Capture
	asr     *asr.Dispatcher
	pinyin  *pinyin.Engine
	inject  *Injector

	// 事件回调
	onModeChange   func(InputMode)
	onStateChange  func(AppState)
	onCandidates   func(*pinyin.CandidateResult)
	onVolume       func(float32)
	onASRResult    func(string, string) // text, type (partial/final)
	onError        func(string)
}

// NewDispatcher 创建输入模式调度器
func NewDispatcher(audioCapture audio.Capture, asrDispatcher *asr.Dispatcher, pinyinEngine *pinyin.Engine, injector *Injector) *Dispatcher {
	return &Dispatcher{
		currentMode: ModeIdle,
		appState:    StateIdle,
		audio:       audioCapture,
		asr:         asrDispatcher,
		pinyin:      pinyinEngine,
		inject:      injector,
	}
}

// SetCallbacks 设置事件回调
func (d *Dispatcher) SetCallbacks(
	onModeChange func(InputMode),
	onStateChange func(AppState),
	onCandidates func(*pinyin.CandidateResult),
	onVolume func(float32),
	onASRResult func(string, string),
	onError func(string),
) {
	d.onModeChange = onModeChange
	d.onStateChange = onStateChange
	d.onCandidates = onCandidates
	d.onVolume = onVolume
	d.onASRResult = onASRResult
	d.onError = onError
}

// StartVoice 开始语音输入（按下快捷键）
func (d *Dispatcher) StartVoice() {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.currentMode == ModeVoice || d.appState == StateRecording {
		return
	}

	// 如果正在键盘输入，清空拼音缓冲
	if d.currentMode == ModeKeyboard {
		d.pinyin.ClearBuf()
	}

	d.currentMode = ModeVoice
	d.setState(StateRecording)

	if d.onModeChange != nil {
		d.onModeChange(ModeVoice)
	}

	audioCh, err := d.audio.Start()
	if err != nil {
		d.onError("启动录音失败: " + err.Error())
		return
	}

	go d.processVoice(audioCh)
}

// StopVoice 停止语音输入（松开快捷键）
func (d *Dispatcher) StopVoice() {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.currentMode != ModeVoice {
		return
	}

	d.setState(StateRecognizing)
	d.audio.Stop()
}

func (d *Dispatcher) processVoice(audioCh <-chan []float32) {
	resultCh, err := d.asr.Recognize(audioCh)
	if err != nil {
		d.mu.Lock()
		d.currentMode = ModeIdle
		d.setState(StateIdle)
		d.mu.Unlock()
		return
	}

	var finalText string

	for result := range resultCh {
		if result.Error != nil {
			d.onError("识别错误: " + result.Error.Error())
			continue
		}

		if result.Type == asr.ResultFinal {
			finalText = result.Text
			d.inject.Inject(finalText)

			d.mu.Lock()
			d.currentMode = ModeIdle
			d.setState(StateInputted)
			d.mu.Unlock()

			if d.onASRResult != nil {
				d.onASRResult(finalText, "final")
			}
			return
		}

		// 中间结果
		if d.onASRResult != nil {
			d.onASRResult(result.Text, "partial")
		}
	}

	d.mu.Lock()
	d.currentMode = ModeIdle
	d.setState(StateIdle)
	d.mu.Unlock()
}

// OnKeyPress 处理键盘按键（拼音输入）
func (d *Dispatcher) OnKeyPress(key rune) *pinyin.CandidateResult {
	d.mu.Lock()

	// 语音模式中检测到键盘输入 → 切换回键盘模式
	if d.currentMode == ModeVoice {
		d.currentMode = ModeKeyboard
		d.setState(StateIdle)
		d.audio.Stop()

		if d.onModeChange != nil {
			d.onModeChange(ModeKeyboard)
		}
	} else if d.currentMode == ModeIdle {
		d.currentMode = ModeKeyboard

		if d.onModeChange != nil {
			d.onModeChange(ModeKeyboard)
		}
	}

	d.mu.Unlock()

	result := d.pinyin.ProcessKey(key)

	if result.Committed != "" {
		d.inject.Inject(result.Committed)

		d.mu.Lock()
		d.currentMode = ModeIdle
		d.setState(StateInputted)
		d.mu.Unlock()
	}

	if d.onCandidates != nil {
		d.onCandidates(result)
	}

	return result
}

// GetCurrentMode 获取当前输入模式
func (d *Dispatcher) GetCurrentMode() InputMode {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.currentMode
}

// GetAppState 获取应用状态
func (d *Dispatcher) GetAppState() AppState {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.appState
}

func (d *Dispatcher) setState(state AppState) {
	d.appState = state
	if d.onStateChange != nil {
		d.onStateChange(state)
	}
}
