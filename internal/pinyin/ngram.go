package pinyin

// BigramModel 二元语言模型（基于词频和上下文排序候选词）
type BigramModel struct {
	freq    map[string]int       // 单个词频率
	bigrams map[string]map[string]int // 前词→后词→共现次数
}

// NewBigramModel 创建二元语言模型
func NewBigramModel() *BigramModel {
	return &BigramModel{
		freq:    make(map[string]int),
		bigrams: make(map[string]map[string]int),
	}
}

// Record 记录选词（用于学习用户习惯）
func (m *BigramModel) Record(prevWord, currentWord string) {
	m.freq[currentWord]++

	if prevWord != "" {
		if m.bigrams[prevWord] == nil {
			m.bigrams[prevWord] = make(map[string]int)
		}
		m.bigrams[prevWord][currentWord]++
	}
}

// Rank 对候选词排序，返回排序后的词条
// prevWord: 前一个已确认的词（用于上下文排序）
func (m *BigramModel) Rank(entries []DictEntry, prevWord string) []DictEntry {
	if len(entries) <= 1 {
		return entries
	}

	// 计算每个候选词的得分
	type scored struct {
		entry DictEntry
		score int
	}

	var scoredList []scored
	for _, e := range entries {
		score := e.Freq + m.freq[e.Word] // 基础词频

		// 如果有上文，加上 bigram 得分
		if prevWord != "" {
			if bigram, ok := m.bigrams[prevWord]; ok {
				score += bigram[e.Word] * 2 // bigram 权重更高
			}
		}

		scoredList = append(scoredList, scored{entry: e, score: score})
	}

	// 按得分降序排列
	for i := 0; i < len(scoredList)-1; i++ {
		for j := i + 1; j < len(scoredList); j++ {
			if scoredList[j].score > scoredList[i].score {
				scoredList[i], scoredList[j] = scoredList[j], scoredList[i]
			}
		}
	}

	result := make([]DictEntry, len(scoredList))
	for i, s := range scoredList {
		result[i] = s.entry
	}
	return result
}

// GetFreq 获取词频
func (m *BigramModel) GetFreq(word string) int {
	return m.freq[word]
}
