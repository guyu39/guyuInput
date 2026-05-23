package config

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"sync"

	"guyuInput/internal/storage"
)

// Manager 配置管理器
type Manager struct {
	mu       sync.RWMutex
	db       *sql.DB
	cache    map[string]string
	watchers map[string][]func(old, new string)
}

// 默认配置
var defaults = map[string]string{
	"asr_mode":          "auto",
	"asr_online_engine": "xunfei",
	"candidate_count":   "5",
	"inject_method":     "auto",
	"floatbar_opacity":  "95",
	"floatbar_position": "center",
	"auto_punctuation":  "true",
	"record_hotkey":     "ctrl+alt+v",
	"xunfei_app_id":     "",
	"xunfei_api_key":    "",
	"xunfei_api_secret": "",
	"first_run":         "true",
}

// NewManager 创建配置管理器
func NewManager() *Manager {
	return &Manager{
		db:       storage.DB(),
		cache:    make(map[string]string),
		watchers: make(map[string][]func(old, new string)),
	}
}

// Load 加载所有配置到缓存
func (m *Manager) Load() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	// 加载默认值
	for k, v := range defaults {
		m.cache[k] = v
	}

	if m.db == nil {
		return nil
	}

	// 从数据库覆盖
	rows, err := m.db.Query(`SELECT key, value FROM config`)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var k, v string
		if err := rows.Scan(&k, &v); err != nil {
			continue
		}
		m.cache[k] = v
	}

	return nil
}

// Get 获取配置项
func (m *Manager) Get(key string) string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if v, ok := m.cache[key]; ok {
		return v
	}
	if v, ok := defaults[key]; ok {
		return v
	}
	return ""
}

// GetInt 获取整数配置
func (m *Manager) GetInt(key string) int {
	var val int
	fmt.Sscanf(m.Get(key), "%d", &val)
	return val
}

// GetBool 获取布尔配置
func (m *Manager) GetBool(key string) bool {
	return m.Get(key) == "true"
}

// Set 设置配置项
func (m *Manager) Set(key, value string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	old := m.cache[key]
	m.cache[key] = value

	if m.db != nil {
		_, err := m.db.Exec(
			`INSERT INTO config (key, value, updated_at) VALUES (?, ?, strftime('%s','now'))
			 ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = strftime('%s','now')`,
			key, value, value,
		)
		if err != nil {
			return err
		}
	}

	// 触发回调
	if watchers, ok := m.watchers[key]; ok {
		for _, cb := range watchers {
			cb(old, value)
		}
	}

	return nil
}

// GetAll 获取所有配置
func (m *Manager) GetAll() map[string]string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make(map[string]string, len(m.cache))
	for k, v := range m.cache {
		result[k] = v
	}
	return result
}

// GetAllJSON 获取所有配置（JSON 字符串）
func (m *Manager) GetAllJSON() string {
	data, _ := json.Marshal(m.GetAll())
	return string(data)
}

// Reset 恢复默认配置
func (m *Manager) Reset() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	for k, v := range defaults {
		m.cache[k] = v
	}

	if m.db != nil {
		_, err := m.db.Exec(`DELETE FROM config`)
		return err
	}
	return nil
}

// OnChange 注册配置变更监听
func (m *Manager) OnChange(key string, callback func(old, new string)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.watchers[key] = append(m.watchers[key], callback)
}
