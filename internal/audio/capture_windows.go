package audio

import (
	"fmt"
	"sync"
	"syscall"
	"unsafe"
)

var (
	winmm            = syscall.NewLazyDLL("winmm.dll")
	waveInOpen       = winmm.NewProc("waveInOpen")
	waveInStart      = winmm.NewProc("waveInStart")
	waveInStop       = winmm.NewProc("waveInStop")
	waveInReset      = winmm.NewProc("waveInReset")
	waveInClose      = winmm.NewProc("waveInClose")
	waveInGetNumDevs = winmm.NewProc("waveInGetNumDevs")
	waveInGetDevCaps = winmm.NewProc("waveInGetDevCapsW")
)

const maxPNameLen = 32

type waveInCaps struct {
	wMid          uint16
	wPid          uint16
	vDriverVersion uint32
	szPname       [maxPNameLen]uint16
	dwFormats     uint32
	wChannels     uint16
	wReserved1    uint16
}

const (
	waveFormatPCM = 1
	waveMapIn     = 1
	whdrDone      = 0x00000001
	wimData       = 0x3C0
	mmSyserrNoerror = 0
)

type waveFormatEx struct {
	wFormatTag      uint16
	nChannels       uint16
	nSamplesPerSec  uint32
	nAvgBytesPerSec uint32
	nBlockAlign     uint16
	wBitsPerSample  uint16
	cbSize          uint16
}

type waveHdr struct {
	lpData          uintptr
	dwBufferLength  uint32
	dwBytesRecorded uint32
	dwUser          uintptr
	dwFlags         uint32
	dwLoops         uint32
	lpNext          uintptr
	reserved        uintptr
}

// WindowsCapture Windows 音频采集实现
type WindowsCapture struct {
	*BaseCapture
	mu        sync.Mutex
	waveIn    uintptr
	buffers   []*waveHdr
	audioData [][]byte
}

// NewCapture 创建 Windows 音频采集器
func NewCapture() *WindowsCapture {
	return &WindowsCapture{
		BaseCapture: NewBaseCapture(),
	}
}

func (c *WindowsCapture) Start() (<-chan []float32, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.state == StateRecording {
		return nil, fmt.Errorf("已经在录音中")
	}

	c.audioCh = make(chan []float32, 100)
	c.stopCh = make(chan struct{})

	// 设置 PCM 格式
	format := waveFormatEx{
		wFormatTag:     waveFormatPCM,
		nChannels:      1,
		nSamplesPerSec: uint32(c.sampleRate),
		wBitsPerSample: 16,
	}
	format.nBlockAlign = format.nChannels * format.wBitsPerSample / 8
	format.nAvgBytesPerSec = format.nSamplesPerSec * uint32(format.nBlockAlign)
	format.cbSize = 0

	// 打开录音设备
	ret, _, _ := waveInOpen.Call(
		uintptr(unsafe.Pointer(&c.waveIn)),
		waveMapIn,
		uintptr(unsafe.Pointer(&format)),
		0, 0, 0,
	)
	if ret != mmSyserrNoerror {
		return nil, fmt.Errorf("打开录音设备失败: %d", ret)
	}

	// 准备缓冲区
	numBuffers := 4
	c.buffers = make([]*waveHdr, numBuffers)
	c.audioData = make([][]byte, numBuffers)

	for i := 0; i < numBuffers; i++ {
		bufSize := c.bufSize * int(format.nBlockAlign)
		data := make([]byte, bufSize)
		c.audioData[i] = data

		hdr := &waveHdr{
			lpData:         uintptr(unsafe.Pointer(&data[0])),
			dwBufferLength: uint32(bufSize),
		}
		c.buffers[i] = hdr

		ret, _, _ := waveInStart.Call(c.waveIn, uintptr(unsafe.Pointer(hdr)), uintptr(unsafe.Sizeof(waveHdr{})))
		if ret != mmSyserrNoerror {
			return nil, fmt.Errorf("准备音频缓冲区失败: %d", ret)
		}
	}

	// 开始录音
	ret, _, _ = waveInStart.Call(c.waveIn)
	if ret != mmSyserrNoerror {
		return nil, fmt.Errorf("开始录音失败: %d", ret)
	}

	c.state = StateRecording

	// 启动采集 goroutine
	go c.captureLoop(format)

	return c.audioCh, nil
}

func (c *WindowsCapture) captureLoop(format waveFormatEx) {
	defer close(c.audioCh)

	for {
		select {
		case <-c.stopCh:
			return
		default:
			// 简化实现：直接从缓冲区读取
			for i, data := range c.audioData {
				samples := make([]float32, len(data)/2)
				for j := 0; j < len(data); j += 2 {
					// 16-bit PCM → float32
					val := int16(data[j]) | int16(data[j+1])<<8
					samples[j/2] = float32(val) / 32768.0
				}

				c.mu.Lock()
				c.setVolume(samples)
				c.mu.Unlock()

				select {
				case c.audioCh <- samples:
				case <-c.stopCh:
					return
				}

				// 重新准备缓冲区
				c.buffers[i].dwBytesRecorded = 0
			}
		}
	}
}

func (c *WindowsCapture) Stop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.state != StateRecording {
		return nil
	}

	close(c.stopCh)
	c.state = StateIdle

	waveInReset.Call(c.waveIn)
	waveInClose.Call(c.waveIn)
	return nil
}

func (c *WindowsCapture) ListDevices() ([]Device, error) {
	ret, _, _ := waveInGetNumDevs.Call()
	count := int(ret)

	devices := make([]Device, 0, count)
	for i := 0; i < count; i++ {
		var caps waveInCaps
		r, _, _ := waveInGetDevCaps.Call(uintptr(i), uintptr(unsafe.Pointer(&caps)), uintptr(unsafe.Sizeof(caps)))
		name := fmt.Sprintf("麦克风 %d", i+1)
		if r == mmSyserrNoerror {
			name = syscall.UTF16ToString(caps.szPname[:])
		}
		devices = append(devices, Device{
			ID:   fmt.Sprintf("%d", i),
			Name: name,
		})
	}
	if len(devices) > 0 {
		devices[0].IsDefault = true
	}
	return devices, nil
}

func (c *WindowsCapture) SelectDevice(deviceID string) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.state == StateRecording {
		return fmt.Errorf("录音中无法切换设备")
	}
	c.deviceID = deviceID
	return nil
}
