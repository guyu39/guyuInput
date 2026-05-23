package storage

import (
	"database/sql"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

var db *sql.DB

// Init 初始化数据库
func Init() error {
	dir, err := dataDir()
	if err != nil {
		return err
	}

	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}

	dbPath := filepath.Join(dir, "guyuinput.db")
	db, err = sql.Open("sqlite", dbPath+"?_journal_mode=WAL&_busy_timeout=5000")
	if err != nil {
		return err
	}

	db.SetMaxOpenConns(1) // SQLite 单写

	if err := migrate(); err != nil {
		return err
	}

	return nil
}

// Close 关闭数据库
func Close() {
	if db != nil {
		db.Close()
	}
}

// DB 获取数据库实例
func DB() *sql.DB {
	return db
}

// dataDir 数据目录
func dataDir() (string, error) {
	appData := os.Getenv("APPDATA")
	if appData == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		appData = filepath.Join(home, "AppData", "Roaming")
	}
	return filepath.Join(appData, "guyuInput"), nil
}

// migrate 数据库迁移
func migrate() error {
	tables := []string{
		`CREATE TABLE IF NOT EXISTS user_dict (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			word       TEXT    NOT NULL,
			pinyin     TEXT    NOT NULL,
			frequency  INTEGER DEFAULT 1,
			dict_type  TEXT    DEFAULT 'user',
			created_at INTEGER DEFAULT (strftime('%s','now')),
			updated_at INTEGER DEFAULT (strftime('%s','now'))
		)`,
		`CREATE INDEX IF NOT EXISTS idx_user_dict_pinyin ON user_dict(pinyin)`,
		`CREATE INDEX IF NOT EXISTS idx_user_dict_freq ON user_dict(frequency DESC)`,

		`CREATE TABLE IF NOT EXISTS config (
			key        TEXT PRIMARY KEY,
			value      TEXT    NOT NULL,
			updated_at INTEGER DEFAULT (strftime('%s','now'))
		)`,

		`CREATE TABLE IF NOT EXISTS input_history (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			text       TEXT    NOT NULL,
			source     TEXT    NOT NULL,
			app_name   TEXT,
			created_at INTEGER DEFAULT (strftime('%s','now'))
		)`,
		`CREATE INDEX IF NOT EXISTS idx_history_date ON input_history(created_at)`,

		`CREATE TABLE IF NOT EXISTS input_stats (
			date        TEXT    PRIMARY KEY,
			voice_chars INTEGER DEFAULT 0,
			kbd_chars   INTEGER DEFAULT 0,
			voice_count INTEGER DEFAULT 0,
			kbd_count   INTEGER DEFAULT 0
		)`,
	}

	for _, ddl := range tables {
		if _, err := db.Exec(ddl); err != nil {
			return err
		}
	}
	return nil
}

// CleanHistory 清理过期历史（保留最近30天）
func CleanHistory() error {
	if db == nil {
		return nil
	}
	_, err := db.Exec(
		`DELETE FROM input_history WHERE created_at < strftime('%s','now') - 2592000`)
	return err
}
