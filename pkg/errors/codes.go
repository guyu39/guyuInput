package errors

import "fmt"

// ErrorCode 统一错误码
type ErrorCode int

const (
	// 通用错误 (1000-1099)
	ErrCodeUnknown        ErrorCode = 1000
	ErrCodeInternal       ErrorCode = 1001
	ErrCodeInvalidParam   ErrorCode = 1002
	ErrCodeNotSupported   ErrorCode = 1003
	ErrCodeTimeout        ErrorCode = 1004
	ErrCodeNotInitialized ErrorCode = 1005

	// 音频相关 (1100-1199)
	ErrCodeAudioDeviceNotFound ErrorCode = 1100
	ErrCodeAudioPermission     ErrorCode = 1101
	ErrCodeAudioDeviceBusy     ErrorCode = 1102
	ErrCodeAudioStreamError    ErrorCode = 1103
	ErrCodeAudioNoVoice        ErrorCode = 1104

	// ASR 相关 (1200-1299)
	ErrCodeASRNetworkError   ErrorCode = 1200
	ErrCodeASRTimeout        ErrorCode = 1201
	ErrCodeASRQuotaExceeded  ErrorCode = 1202
	ErrCodeASRAuthFailed     ErrorCode = 1203
	ErrCodeASRModelNotFound  ErrorCode = 1204
	ErrCodeASRModelLoadFailed ErrorCode = 1205
	ErrCodeASRNoResult       ErrorCode = 1206

	// 键盘输入相关 (1300-1399)
	ErrCodePinyinInvalid     ErrorCode = 1300
	ErrCodePinyinAmbiguous   ErrorCode = 1301
	ErrCodeDictNotFound      ErrorCode = 1302
	ErrCodeDictImportFailed  ErrorCode = 1303
	ErrCodeDictFormatInvalid ErrorCode = 1304

	// 文本注入相关 (1400-1499)
	ErrCodeInjectBlocked   ErrorCode = 1400
	ErrCodeInjectClipboard ErrorCode = 1401
	ErrCodeInjectNoTarget  ErrorCode = 1402

	// 配置相关 (1500-1599)
	ErrCodeConfigNotFound ErrorCode = 1500
	ErrCodeConfigInvalid  ErrorCode = 1501
	ErrCodeDBError        ErrorCode = 1502
)

// codeMessages 错误码对应的默认消息
var codeMessages = map[ErrorCode]string{
	ErrCodeUnknown:             "未知错误",
	ErrCodeInternal:            "内部错误",
	ErrCodeInvalidParam:        "参数无效",
	ErrCodeNotSupported:        "不支持的操作",
	ErrCodeTimeout:             "操作超时",
	ErrCodeNotInitialized:      "模块未初始化",
	ErrCodeAudioDeviceNotFound: "未找到音频设备",
	ErrCodeAudioPermission:     "麦克风权限不足",
	ErrCodeAudioDeviceBusy:     "音频设备被占用",
	ErrCodeAudioStreamError:    "音频流错误",
	ErrCodeAudioNoVoice:        "未检测到语音输入",
	ErrCodeASRNetworkError:     "网络连接失败",
	ErrCodeASRTimeout:          "语音识别超时",
	ErrCodeASRQuotaExceeded:    "API 配额用尽",
	ErrCodeASRAuthFailed:       "API 鉴权失败",
	ErrCodeASRModelNotFound:    "离线语音模型未找到",
	ErrCodeASRModelLoadFailed:  "离线语音模型加载失败",
	ErrCodeASRNoResult:         "未识别到有效结果",
	ErrCodePinyinInvalid:       "无效拼音",
	ErrCodePinyinAmbiguous:     "拼音存在歧义",
	ErrCodeDictNotFound:        "词库未找到",
	ErrCodeDictImportFailed:    "词库导入失败",
	ErrCodeDictFormatInvalid:   "词库格式无效",
	ErrCodeInjectBlocked:       "文本注入被目标应用拦截",
	ErrCodeInjectClipboard:     "剪贴板操作失败",
	ErrCodeInjectNoTarget:      "未找到可注入的目标窗口",
	ErrCodeConfigNotFound:      "配置项不存在",
	ErrCodeConfigInvalid:       "配置值无效",
	ErrCodeDBError:             "数据库错误",
}

// AppError 应用错误
type AppError struct {
	Code    ErrorCode
	Message string
	Cause   error
}

func (e *AppError) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("[%d] %s: %v", e.Code, e.Message, e.Cause)
	}
	return fmt.Sprintf("[%d] %s", e.Code, e.Message)
}

func (e *AppError) Unwrap() error {
	return e.Cause
}

// New 创建应用错误
func New(code ErrorCode, msg string) *AppError {
	return &AppError{Code: code, Message: msg}
}

// Newf 创建格式化消息的应用错误
func Newf(code ErrorCode, format string, args ...interface{}) *AppError {
	return &AppError{Code: code, Message: fmt.Sprintf(format, args...)}
}

// Wrap 包装底层错误
func Wrap(code ErrorCode, msg string, cause error) *AppError {
	return &AppError{Code: code, Message: msg, Cause: cause}
}

// DefaultMsg 获取错误码的默认消息
func (c ErrorCode) DefaultMsg() string {
	if msg, ok := codeMessages[c]; ok {
		return msg
	}
	return "未知错误"
}

// Int 返回 int 类型的错误码
func (c ErrorCode) Int() int {
	return int(c)
}
