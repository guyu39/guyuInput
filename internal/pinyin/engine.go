package pinyin

import (
	"strings"
	"sync"

	"guyuInput/internal/dict"
)

// CandidateResult 候选词结果
type CandidateResult struct {
	Pinyin     string   `json:"pinyin"`
	Candidates []string `json:"candidates"`
	Committed  string   `json:"committed"`
	IsComplete bool     `json:"is_complete"`
}

// Engine 拼音输入引擎
type Engine struct {
	mu          sync.Mutex
	pinyinBuf   string
	candidates  []DictEntry
	prevWord    string // 前一个已确认的词（用于 bigram 上下文）
	trie        *Trie
	ngram       *BigramModel
	dictManager *dict.Manager
	maxCandidates int
}

// NewEngine 创建拼音引擎
func NewEngine(dictMgr *dict.Manager) *Engine {
	e := &Engine{
		trie:         NewTrie(),
		ngram:        NewBigramModel(),
		dictManager:  dictMgr,
		maxCandidates: 5,
	}

	// 加载内置词库到 Trie
	for pinyin, entries := range dictBuiltinEntries() {
		for _, entry := range entries {
			e.trie.Insert(pinyin, entry)
		}
	}

	return e
}

// ProcessKey 处理按键事件
func (e *Engine) ProcessKey(key rune) *CandidateResult {
	e.mu.Lock()
	defer e.mu.Unlock()

	switch {
	case key >= 'a' && key <= 'z':
		return e.handleLetter(byte(key))

	case key >= '0' && key <= '9':
		return e.handleNumber(int(key - '0'))

	case key == ' ':
		return e.handleSpace()

	case key == '\b':
		return e.handleBackspace()

	case key == '\'':
		// 分隔符，用于处理 xi'an 这类音节
		e.pinyinBuf += "'"
		return e.searchCandidates()
	}

	return e.emptyResult()
}

func (e *Engine) handleLetter(ch byte) *CandidateResult {
	e.pinyinBuf += string(ch)
	return e.searchCandidates()
}

func (e *Engine) handleNumber(n int) *CandidateResult {
	if n == 0 {
		return e.emptyResult()
	}

	idx := n - 1
	if idx < len(e.candidates) {
		word := e.candidates[idx].Word
		e.ngram.Record(e.prevWord, word)
		e.prevWord = word
		e.pinyinBuf = ""
		e.candidates = nil
		return &CandidateResult{
			Committed:  word,
			IsComplete: true,
		}
	}

	return e.emptyResult()
}

func (e *Engine) handleSpace() *CandidateResult {
	if len(e.candidates) > 0 {
		word := e.candidates[0].Word
		e.ngram.Record(e.prevWord, word)
		e.prevWord = word
		e.pinyinBuf = ""
		e.candidates = nil
		return &CandidateResult{
			Committed:  word,
			IsComplete: true,
		}
	}
	return e.emptyResult()
}

func (e *Engine) handleBackspace() *CandidateResult {
	if len(e.pinyinBuf) > 0 {
		// 处理可能的 UTF-8 字符（拼音分隔符是 ASCII，所以直接用 byte 长度）
		e.pinyinBuf = e.pinyinBuf[:len(e.pinyinBuf)-1]
	}
	if e.pinyinBuf == "" {
		e.candidates = nil
		return e.emptyResult()
	}
	return e.searchCandidates()
}

func (e *Engine) searchCandidates() *CandidateResult {
	syllables := Segment(e.pinyinBuf)
	query := strings.Join(syllables, "")

	// 先从 Trie 搜索
	entries := e.trie.Search(query)

	// Trie 未命中则查数据库词库
	if len(entries) == 0 && e.dictManager != nil {
		dictEntries, _ := e.dictManager.Search(query, e.maxCandidates)
		for _, de := range dictEntries {
			entries = append(entries, DictEntry{Word: de.Word, Freq: de.Freq})
		}
	}

	// 通过 ngram 排序
	entries = e.ngram.Rank(entries, e.prevWord)

	// 限制候选词数量
	if len(entries) > e.maxCandidates {
		entries = entries[:e.maxCandidates]
	}

	e.candidates = entries

	candidateWords := make([]string, len(entries))
	for i, entry := range entries {
		candidateWords[i] = entry.Word
	}

	return &CandidateResult{
		Pinyin:     e.pinyinBuf,
		Candidates: candidateWords,
	}
}

// GetPinyinBuf 获取当前拼音缓冲区
func (e *Engine) GetPinyinBuf() string {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.pinyinBuf
}

// ClearBuf 清空拼音缓冲区
func (e *Engine) ClearBuf() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.pinyinBuf = ""
	e.candidates = nil
}

// Reset 重置引擎状态
func (e *Engine) Reset() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.pinyinBuf = ""
	e.candidates = nil
}

// emptyResult 空结果
func (e *Engine) emptyResult() *CandidateResult {
	candidateWords := make([]string, len(e.candidates))
	for i, entry := range e.candidates {
		candidateWords[i] = entry.Word
	}
	return &CandidateResult{
		Pinyin:     e.pinyinBuf,
		Candidates: candidateWords,
	}
}

// dictBuiltinEntries 内置词库条目
func dictBuiltinEntries() map[string][]DictEntry {
	result := make(map[string][]DictEntry)
	for pinyin, entries := range dict.BuiltinEntries() {
		for _, e := range entries {
			result[pinyin] = append(result[pinyin], DictEntry{Word: e.Word, Freq: e.Freq})
		}
	}
	return result
}
