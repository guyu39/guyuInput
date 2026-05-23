package logger

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/natefinch/lumberjack"
)

// Level 日志级别
type Level string

const (
	LevelDebug Level = "DEBUG"
	LevelInfo  Level = "INFO"
	LevelWarn  Level = "WARN"
	LevelError Level = "ERROR"
	LevelFatal Level = "FATAL"
)

// Entry 日志条目
type Entry struct {
	Level   Level  `json:"level"`
	Ts      string `json:"ts"`
	Msg     string `json:"msg"`
	File    string `json:"file,omitempty"`
	ErrCode int    `json:"error_code,omitempty"`
	TraceID string `json:"trace_id,omitempty"`
	Extra   any    `json:"extra,omitempty"`
}

var writer io.Writer

// Init 初始化日志模块
func Init() {
	dir, err := logDir()
	if err != nil {
		log.Printf("无法获取日志目录: %v，降级到 stderr", err)
		writer = os.Stderr
		return
	}

	os.MkdirAll(dir, 0700)

	writer = &lumberjack.Logger{
		Filename:   filepath.Join(dir, "guyuinput.log"),
		MaxSize:    10, // MB
		MaxBackups: 7,
		MaxAge:     7, // days
		Compress:   false,
	}

	log.SetOutput(writer)
	log.SetFlags(0) // 自定义格式
}

func logDir() (string, error) {
	appData := os.Getenv("APPDATA")
	if appData == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		appData = filepath.Join(home, "AppData", "Roaming")
	}
	return filepath.Join(appData, "guyuInput", "logs"), nil
}

func logEntry(level Level, msg string, errCode int, traceID string, extra any) {
	entry := Entry{
		Level:   level,
		Ts:      time.Now().UTC().Format(time.RFC3339),
		Msg:     msg,
		ErrCode: errCode,
		TraceID: traceID,
		Extra:   extra,
	}

	// Debug/Error 级别附加调用位置
	if level == LevelDebug || level == LevelError {
		_, file, line, ok := runtime.Caller(2)
		if ok {
			entry.File = fmt.Sprintf("%s:%d", filepath.Base(file), line)
		}
	}

	data, _ := json.Marshal(entry)
	if writer != nil {
		writer.Write(append(data, '\n'))
	} else {
		log.Println(string(data))
	}
}

func Debug(msg string) {
	logEntry(LevelDebug, msg, 0, "", nil)
}

func Debugf(format string, args ...interface{}) {
	logEntry(LevelDebug, fmt.Sprintf(format, args...), 0, "", nil)
}

func Info(msg string) {
	logEntry(LevelInfo, msg, 0, "", nil)
}

func Infof(format string, args ...interface{}) {
	logEntry(LevelInfo, fmt.Sprintf(format, args...), 0, "", nil)
}

func Warn(msg string) {
	logEntry(LevelWarn, msg, 0, "", nil)
}

func Warnf(format string, args ...interface{}) {
	logEntry(LevelWarn, fmt.Sprintf(format, args...), 0, "", nil)
}

func Error(msg string) {
	logEntry(LevelError, msg, 0, "", nil)
}

func Errorf(format string, args ...interface{}) {
	logEntry(LevelError, fmt.Sprintf(format, args...), 0, "", nil)
}

func ErrorWithCode(msg string, errCode int, traceID string) {
	logEntry(LevelError, msg, errCode, traceID, nil)
}

func Fatal(msg string) {
	logEntry(LevelFatal, msg, 0, "", nil)
	os.Exit(1)
}

func Fatalf(format string, args ...interface{}) {
	logEntry(LevelFatal, fmt.Sprintf(format, args...), 0, "", nil)
	os.Exit(1)
}
