package audio

import (
	"math"
	"sync"
)

// Device 音频设备信息
type Device struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	IsDefault bool  `json:"is_default"`
}

// Capture 音频采集器接口
type Capture interface {
	Start() (<-chan []float32, error)
	Stop() error
	Volume() float32
	IsRecording() bool
	ListDevices() ([]Device, error)
	SelectDevice(deviceID string) error
}

// State 采集器状态
type State int

const (
	StateIdle     State = iota
	StateRecording
	StateError
)

// BaseCapture 基础采集器（提供通用逻辑）
type BaseCapture struct {
	mu        sync.Mutex
	state     State
	audioCh   chan []float32
	stopCh    chan struct{}
	volume    float32
	deviceID  string
	bufSize   int
	sampleRate int
}

// NewBaseCapture 创建基础采集器
func NewBaseCapture() *BaseCapture {
	return &BaseCapture{
		state:      StateIdle,
		bufSize:    1024,
		sampleRate: 16000,
	}
}

func (c *BaseCapture) IsRecording() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.state == StateRecording
}

func (c *BaseCapture) Volume() float32 {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.volume
}

func (c *BaseCapture) setVolume(samples []float32) {
	var sum float64
	for _, s := range samples {
		sum += float64(s * s)
	}
	rms := float32(math.Sqrt(sum / float64(len(samples))))
	c.volume = rms
}

// DefaultCapture 默认采集器实现（使用 Windows WaveIn API）
// 在 capture_windows.go 中实现
