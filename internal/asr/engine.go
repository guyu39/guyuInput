package asr

import (
	"context"
	"fmt"
	"sync"
	"time"

	"guyuInput/internal/logger"
)

// ASRMode 识别模式
type ASRMode string

const (
	ModeOnline  ASRMode = "online"
	ModeOffline ASRMode = "offline"
	ModeAuto    ASRMode = "auto"
)

// ResultType 结果类型
type ResultType string

const (
	ResultPartial ResultType = "partial" // 中间结果
	ResultFinal   ResultType = "final"   // 最终结果
)

// RecognitionResult 识别结果
type RecognitionResult struct {
	Type  ResultType
	Text  string
	Error error
}

// Engine ASR 引擎接口
type Engine interface {
	Recognize(audioCh <-chan []float32) (<-chan RecognitionResult, error)
	Mode() ASRMode
	Close() error
}

// Dispatcher ASR 调度器（在线/离线自动切换）
type Dispatcher struct {
	mu      sync.Mutex
	online  Engine
	offline Engine
	mode    ASRMode
}

// NewDispatcher 创建 ASR 调度器
func NewDispatcher(online, offline Engine, mode ASRMode) *Dispatcher {
	return &Dispatcher{
		online:  online,
		offline: offline,
		mode:    mode,
	}
}

// Recognize 执行语音识别
func (d *Dispatcher) Recognize(audioCh <-chan []float32) (<-chan RecognitionResult, error) {
	d.mu.Lock()
	mode := d.mode
	d.mu.Unlock()

	switch mode {
	case ModeOnline:
		if d.online == nil {
			return nil, fmt.Errorf("在线引擎未配置")
		}
		return d.online.Recognize(audioCh)

	case ModeOffline:
		if d.offline == nil {
			return nil, fmt.Errorf("离线引擎未配置")
		}
		return d.offline.Recognize(audioCh)

	case ModeAuto:
		if d.online == nil {
			if d.offline == nil {
				return nil, fmt.Errorf("无可用的 ASR 引擎")
			}
			return d.offline.Recognize(audioCh)
		}

		resultCh := make(chan RecognitionResult, 10)
		go func() {
			defer close(resultCh)

			onlineCh, err := d.online.Recognize(audioCh)
			if err != nil {
				logger.Warnf("在线识别启动失败，降级离线: %v", err)
				d.tryOffline(audioCh, resultCh)
				return
			}

			firstResult := true
			for result := range onlineCh {
				if result.Error != nil && firstResult {
					logger.Warnf("在线识别失败，降级离线: %v", result.Error)
					d.tryOffline(audioCh, resultCh)
					return
				}
				firstResult = false
				resultCh <- result
			}
		}()
		return resultCh, nil
	}

	return nil, fmt.Errorf("未知的 ASR 模式: %s", mode)
}

func (d *Dispatcher) tryOffline(audioCh <-chan []float32, resultCh chan<- RecognitionResult) {
	if d.offline == nil {
		resultCh <- RecognitionResult{
			Error: fmt.Errorf("离线引擎未配置"),
		}
		return
	}

	d.mu.Lock()
	d.mode = ModeOffline
	d.mu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	offlineCh, err := d.offline.Recognize(audioCh)
	if err != nil {
		resultCh <- RecognitionResult{Error: err}
		return
	}

	for {
		select {
		case result, ok := <-offlineCh:
			if !ok {
				return
			}
			resultCh <- result
		case <-ctx.Done():
			return
		}
	}
}

// Mode 获取当前模式
func (d *Dispatcher) Mode() ASRMode {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.mode
}

// SetMode 设置模式
func (d *Dispatcher) SetMode(mode ASRMode) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.mode = mode
}

// Close 释放资源
func (d *Dispatcher) Close() error {
	if d.online != nil {
		d.online.Close()
	}
	if d.offline != nil {
		d.offline.Close()
	}
	return nil
}
