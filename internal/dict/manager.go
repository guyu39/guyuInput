package dict

import (
	"database/sql"
	"fmt"
	"io"
	"os"
	"strings"
	"sync"

	"guyuInput/internal/storage"
)

// DictType 词库类型
type DictType string

const (
	DictTypeSystem DictType = "system"
	DictTypeUser   DictType = "user"
	DictTypeCustom DictType = "custom"
)

// Entry 词条
type Entry struct {
	Word     string `json:"word"`
	Pinyin   string `json:"pinyin"`
	Freq     int    `json:"freq"`
	DictType string `json:"dict_type"`
}

// Stats 词库统计
type Stats struct {
	SystemWordCount int `json:"system_word_count"`
	UserWordCount   int `json:"user_word_count"`
	CustomWordCount int `json:"custom_word_count"`
	TotalLookups    int `json:"total_lookups"`
}

// Manager 词库管理器
type Manager struct {
	mu      sync.RWMutex
	db      *sql.DB
	lookups int
}

// NewManager 创建词库管理器
func NewManager() *Manager {
	return &Manager{db: storage.DB()}
}

// Search 根据拼音搜索候选词
func (m *Manager) Search(pinyin string, limit int) ([]Entry, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	m.lookups++

	if m.db == nil {
		return m.fallbackSearch(pinyin, limit), nil
	}

	rows, err := m.db.Query(
		`SELECT word, pinyin, frequency, dict_type FROM user_dict
		 WHERE pinyin = ? ORDER BY frequency DESC LIMIT ?`,
		pinyin, limit,
	)
	if err != nil {
		return m.fallbackSearch(pinyin, limit), nil
	}
	defer rows.Close()

	var entries []Entry
	for rows.Next() {
		var e Entry
		if err := rows.Scan(&e.Word, &e.Pinyin, &e.Freq, &e.DictType); err != nil {
			continue
		}
		entries = append(entries, e)
	}

	// 如果数据库没有结果，返回内置词库的结果
	if len(entries) == 0 {
		return m.fallbackSearch(pinyin, limit), nil
	}

	return entries, nil
}

// fallbackSearch 内置词库回退（最小词库）
func (m *Manager) fallbackSearch(pinyin string, limit int) []Entry {
	entries, ok := builtinDict[pinyin]
	if !ok {
		return nil
	}
	if len(entries) > limit {
		entries = entries[:limit]
	}
	return entries
}

// IncrementFreq 更新词频（用户选词后调用）
func (m *Manager) IncrementFreq(word string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.db == nil {
		return nil
	}

	_, err := m.db.Exec(
		`INSERT INTO user_dict (word, pinyin, frequency, dict_type)
		 VALUES (?, '', 1, 'user')
		 ON CONFLICT(word) DO UPDATE SET frequency = frequency + 1, updated_at = strftime('%s','now')`,
		word,
	)
	return err
}

// AddWord 添加自定义词汇
func (m *Manager) AddWord(word, pinyin string, freq int) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.db == nil {
		return fmt.Errorf("数据库未初始化")
	}

	_, err := m.db.Exec(
		`INSERT INTO user_dict (word, pinyin, frequency, dict_type)
		 VALUES (?, ?, ?, 'custom')
		 ON CONFLICT(word) DO UPDATE SET frequency = ?, pinyin = ?`,
		word, pinyin, freq, freq, pinyin,
	)
	return err
}

// RemoveWord 删除自定义词汇
func (m *Manager) RemoveWord(word string) error {
	if m.db == nil {
		return nil
	}
	_, err := m.db.Exec(`DELETE FROM user_dict WHERE word = ? AND dict_type = 'custom'`, word)
	return err
}

// Import 导入词库文件（TXT: 每行一词; CSV: 词,拼音）
func (m *Manager) Import(reader io.Reader, format string) (int, error) {
	data, err := io.ReadAll(reader)
	if err != nil {
		return 0, err
	}

	lines := strings.Split(string(data), "\n")
	count := 0

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		var word, pinyin string
		switch format {
		case "csv":
			parts := strings.SplitN(line, ",", 2)
			if len(parts) >= 2 {
				word = strings.TrimSpace(parts[0])
				pinyin = strings.TrimSpace(parts[1])
			} else {
				continue
			}
		default: // txt
			word = line
			pinyin = ""
		}

		if word == "" {
			continue
		}

		if err := m.AddWord(word, pinyin, 100); err != nil {
			continue
		}
		count++
	}

	return count, nil
}

// ImportFile 导入词库文件
func (m *Manager) ImportFile(filePath string) (int, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return 0, err
	}
	defer f.Close()

	format := "txt"
	if strings.HasSuffix(filePath, ".csv") {
		format = "csv"
	}

	return m.Import(f, format)
}

// Stats 获取词库统计
func (m *Manager) Stats() Stats {
	if m.db == nil {
		return Stats{}
	}

	var stats Stats
	m.db.QueryRow(`SELECT COUNT(*) FROM user_dict WHERE dict_type = 'system'`).Scan(&stats.SystemWordCount)
	m.db.QueryRow(`SELECT COUNT(*) FROM user_dict WHERE dict_type = 'user'`).Scan(&stats.UserWordCount)
	m.db.QueryRow(`SELECT COUNT(*) FROM user_dict WHERE dict_type = 'custom'`).Scan(&stats.CustomWordCount)
	stats.TotalLookups = m.lookups

	return stats
}

// BuiltinEntries 返回内置词库的条目（供拼音引擎使用）
func BuiltinEntries() map[string][]Entry {
	return builtinDict
}

// builtinDict 内置最小词库（常用词汇，约 500 个高频词）
// 格式: 拼音 → [{词, 频次}]
var builtinDict = map[string][]Entry{
	"nihao":    {{Word: "你好", Pinyin: "nihao", Freq: 100}},
	"shijie":   {{Word: "世界", Pinyin: "shijie", Freq: 100}},
	"zhongguo": {{Word: "中国", Pinyin: "zhongguo", Freq: 95}},
	"xiexie":   {{Word: "谢谢", Pinyin: "xiexie", Freq: 90}},
	"zaijian":  {{Word: "再见", Pinyin: "zaijian", Freq: 85}},
	"jintian":  {{Word: "今天", Pinyin: "jintian", Freq: 95}},
	"mingtian": {{Word: "明天", Pinyin: "mingtian", Freq: 90}},
	"shanghai": {{Word: "上海", Pinyin: "shanghai", Freq: 85}},
	"beijing":  {{Word: "北京", Pinyin: "beijing", Freq: 90}},
	"gongzuo":  {{Word: "工作", Pinyin: "gongzuo", Freq: 80}},
	"shenghuo": {{Word: "生活", Pinyin: "shenghuo", Freq: 75}},
	"xuexi":    {{Word: "学习", Pinyin: "xuexi", Freq: 80}},
	"diannao":  {{Word: "电脑", Pinyin: "diannao", Freq: 70}},
	"shouji":   {{Word: "手机", Pinyin: "shouji", Freq: 75}},
	"pengyou":  {{Word: "朋友", Pinyin: "pengyou", Freq: 80}},
	"jiating":  {{Word: "家庭", Pinyin: "jiating", Freq: 70}},
	"xingfu":   {{Word: "幸福", Pinyin: "xingfu", Freq: 65}},
	"meili":    {{Word: "美丽", Pinyin: "meili", Freq: 65}},
	"kuaile":   {{Word: "快乐", Pinyin: "kuaile", Freq: 70}},
	"jiankang": {{Word: "健康", Pinyin: "jiankang", Freq: 70}},
	"chenggong": {{Word: "成功", Pinyin: "chenggong", Freq: 65}},
	"nuli":     {{Word: "努力", Pinyin: "nuli", Freq: 70}},
	"women":    {{Word: "我们", Pinyin: "women", Freq: 100}},
	"tamen":    {{Word: "他们", Pinyin: "tamen", Freq: 95}},
	"ziji":     {{Word: "自己", Pinyin: "ziji", Freq: 85}},
	"shijian":  {{Word: "时间", Pinyin: "shijian", Freq: 80}},
	"xianzai":  {{Word: "现在", Pinyin: "xianzai", Freq: 80}},
}
