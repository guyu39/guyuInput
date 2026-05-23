package asr

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"time"

	"github.com/gorilla/websocket"
)

const xunfeiHost = "iat-api.xfyun.cn"

// XunfeiClient 讯飞语音识别客户端
type XunfeiClient struct {
	appID  string
	apiKey string
	secret string
	conn   *websocket.Conn
	done   chan struct{}
}

// NewXunfeiClient 创建讯飞客户端
// 从环境变量读取: XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET
func NewXunfeiClient() *XunfeiClient {
	return &XunfeiClient{
		appID:  os.Getenv("XUNFEI_APP_ID"),
		apiKey: os.Getenv("XUNFEI_API_KEY"),
		secret: os.Getenv("XUNFEI_API_SECRET"),
		done:   make(chan struct{}),
	}
}

func (c *XunfeiClient) Mode() ASRMode {
	return ModeOnline
}

func (c *XunfeiClient) Recognize(audioCh <-chan []float32) (<-chan RecognitionResult, error) {
	if c.appID == "" || c.apiKey == "" || c.secret == "" {
		return nil, fmt.Errorf("讯飞 API 密钥未配置，请设置环境变量 XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET")
	}

	// 构建 WebSocket 连接
	wsURL := c.buildURL()
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		return nil, fmt.Errorf("连接讯飞服务失败: %w", err)
	}
	c.conn = conn

	resultCh := make(chan RecognitionResult, 10)

	go func() {
		defer close(resultCh)
		defer conn.Close()

		// 发送音频数据
		go c.sendAudio(audioCh)

		// 接收识别结果
		c.receiveResults(resultCh)
	}()

	return resultCh, nil
}

func (c *XunfeiClient) buildURL() string {
	now := time.Now().UTC()
	date := now.Format("Mon, 02 Jan 2006 15:04:05 GMT")

	tmp := fmt.Sprintf("host: %s\ndate: %s\nGET /v2/iat HTTP/1.1", xunfeiHost, date)
	mac := hmac.New(sha256.New, []byte(c.secret))
	mac.Write([]byte(tmp))
	signature := base64.StdEncoding.EncodeToString(mac.Sum(nil))

	auth := fmt.Sprintf(
		`api_key="%s",algorithm="hmac-sha256",headers="host date request-line",signature="%s"`,
		c.apiKey, signature,
	)

	u := url.URL{
		Scheme: "wss",
		Host:   xunfeiHost,
		Path:   "/v2/iat",
		RawQuery: fmt.Sprintf(
			"host=%s&date=%s&authorization=%s",
			url.QueryEscape(xunfeiHost),
			url.QueryEscape(date),
			url.QueryEscape(auth),
		),
	}
	return u.String()
}

func (c *XunfeiClient) sendAudio(audioCh <-chan []float32) {
	defer c.conn.WriteMessage(websocket.TextMessage, []byte(`{"data":{"status":2}}`)) // 结束标志

	// 发送首帧（参数帧）
	firstFrame := map[string]interface{}{
		"common": map[string]interface{}{
			"app_id": c.appID,
		},
		"business": map[string]interface{}{
			"language": "zh_cn",
			"domain":   "iat",
			"accent":   "mandarin",
			"vad_eos":  2000,
			"dwa":      "wpgs",
		},
		"data": map[string]interface{}{
			"status":   0,
			"format":   "audio/L16;rate=16000",
			"encoding": "raw",
			"audio":    "",
		},
	}
	frameJSON, _ := json.Marshal(firstFrame)
	c.conn.WriteMessage(websocket.TextMessage, frameJSON)

	// 发送音频数据帧
	for samples := range audioCh {
		audioData := float32ToPCM16(samples)
		frame := map[string]interface{}{
			"data": map[string]interface{}{
				"status": 1,
				"format": "audio/L16;rate=16000",
				"audio":  base64.StdEncoding.EncodeToString(audioData),
			},
		}
		frameJSON, _ := json.Marshal(frame)
		if err := c.conn.WriteMessage(websocket.TextMessage, frameJSON); err != nil {
			return
		}
	}
}

// xunfeiResponse 讯飞响应格式
type xunfeiResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    struct {
		Result struct {
			Ws []struct {
				Cw []struct {
					W string `json:"w"`
				} `json:"cw"`
			} `json:"ws"`
		} `json:"result"`
		Status int `json:"status"`
	} `json:"data"`
}

func (c *XunfeiClient) receiveResults(resultCh chan<- RecognitionResult) {
	for {
		_, msg, err := c.conn.ReadMessage()
		if err != nil {
			resultCh <- RecognitionResult{Error: err}
			return
		}

		var resp xunfeiResponse
		if err := json.Unmarshal(msg, &resp); err != nil {
			continue
		}

		if resp.Code != 0 {
			resultCh <- RecognitionResult{
				Error: fmt.Errorf("讯飞错误 [%d]: %s", resp.Code, resp.Message),
			}
			return
		}

		// 拼接识别文本
		var text string
		for _, ws := range resp.Data.Result.Ws {
			for _, cw := range ws.Cw {
				text += cw.W
			}
		}

		if text == "" {
			continue
		}

		// status: 0=首帧 1=中间帧 2=结束帧
		resultType := ResultPartial
		if resp.Data.Status == 2 {
			resultType = ResultFinal
		}

		resultCh <- RecognitionResult{Type: resultType, Text: text}

		if resp.Data.Status == 2 {
			return
		}
	}
}

func (c *XunfeiClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// float32ToPCM16 将 float32 音频样本转为 16-bit PCM
func float32ToPCM16(samples []float32) []byte {
	data := make([]byte, len(samples)*2)
	for i, s := range samples {
		// 限幅
		if s > 1.0 {
			s = 1.0
		} else if s < -1.0 {
			s = -1.0
		}
		val := int16(s * 32767)
		data[i*2] = byte(val)
		data[i*2+1] = byte(val >> 8)
	}
	return data
}
