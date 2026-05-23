package result

import (
	"crypto/rand"
	"fmt"
	"math"
	"time"
)

// Result 统一结果封装
type Result[T any] struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    T      `json:"data"`
	TraceID string `json:"trace_id"`
	Ts      int64  `json:"ts"`
}

// PageResult 分页结果
type PageResult[T any] struct {
	Items      []T   `json:"items"`
	Total      int64 `json:"total"`
	Page       int   `json:"page"`
	PageSize   int   `json:"page_size"`
	TotalPages int   `json:"total_pages"`
}

// PageRequest 分页请求
type PageRequest struct {
	Page     int `json:"page"`
	PageSize int `json:"page_size"`
}

// NewTraceID 生成追踪ID
func NewTraceID() string {
	b := make([]byte, 4)
	rand.Read(b)
	return fmt.Sprintf("%x-%x", time.Now().UnixNano()/1e6, b)
}

// Ok 成功结果
func Ok[T any](data T) Result[T] {
	return Result[T]{
		Code:    0,
		Message: "ok",
		Data:    data,
		TraceID: NewTraceID(),
		Ts:      time.Now().UnixMilli(),
	}
}

// OkWithMsg 带消息的成功结果
func OkWithMsg[T any](data T, msg string) Result[T] {
	return Result[T]{
		Code:    0,
		Message: msg,
		Data:    data,
		TraceID: NewTraceID(),
		Ts:      time.Now().UnixMilli(),
	}
}

// Err 错误结果
func Err[T any](code int, msg string) Result[T] {
	return Result[T]{
		Code:    code,
		Message: msg,
		TraceID: NewTraceID(),
		Ts:      time.Now().UnixMilli(),
	}
}

// ErrWithData 带数据的错误结果
func ErrWithData[T any](code int, msg string, data T) Result[T] {
	return Result[T]{
		Code:    code,
		Message: msg,
		Data:    data,
		TraceID: NewTraceID(),
		Ts:      time.Now().UnixMilli(),
	}
}

// PageOk 分页成功结果
func PageOk[T any](items []T, total int64, page, pageSize int) Result[PageResult[T]] {
	totalPages := int(math.Ceil(float64(total) / float64(pageSize)))
	return Ok(PageResult[T]{
		Items:      items,
		Total:      total,
		Page:       page,
		PageSize:   pageSize,
		TotalPages: totalPages,
	})
}

// IsOk 判断是否成功
func (r Result[T]) IsOk() bool {
	return r.Code == 0
}
