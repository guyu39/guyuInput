package retry

import (
	"fmt"
	"time"
)

// Policy 重试策略
type Policy struct {
	MaxRetries int
	BaseDelay  time.Duration
	MaxDelay   time.Duration
	Multiplier float64
}

// 预定义策略
var (
	// NetworkPolicy 网络请求重试：3次，100ms → 200ms → 400ms
	NetworkPolicy = Policy{
		MaxRetries: 3,
		BaseDelay:  100 * time.Millisecond,
		MaxDelay:   2 * time.Second,
		Multiplier: 2.0,
	}

	// ClipboardPolicy 剪贴板重试：3次，50ms → 100ms → 200ms
	ClipboardPolicy = Policy{
		MaxRetries: 3,
		BaseDelay:  50 * time.Millisecond,
		MaxDelay:   500 * time.Millisecond,
		Multiplier: 2.0,
	}

	// NoRetry 不重试
	NoRetry = Policy{
		MaxRetries: 0,
	}
)

// Do 通用重试执行器
func Do[T any](policy Policy, fn func() (T, error)) (T, error) {
	var lastErr error
	delay := policy.BaseDelay

	for i := 0; i <= policy.MaxRetries; i++ {
		result, err := fn()
		if err == nil {
			return result, nil
		}
		lastErr = err

		if i < policy.MaxRetries {
			time.Sleep(delay)
			delay = time.Duration(float64(delay) * policy.Multiplier)
			if delay > policy.MaxDelay {
				delay = policy.MaxDelay
			}
		}
	}

	var zero T
	return zero, fmt.Errorf("retry exhausted after %d attempts: %w",
		policy.MaxRetries+1, lastErr)
}
