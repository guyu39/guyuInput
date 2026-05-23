package pinyin

// TrieNode 前缀树节点
type TrieNode struct {
	children map[rune]*TrieNode
	entries  []DictEntry // 该拼音对应的词条列表
	isEnd    bool
}

// DictEntry 词典条目
type DictEntry struct {
	Word string
	Freq int
}

// Trie 拼音前缀树
type Trie struct {
	root *TrieNode
}

// NewTrie 创建前缀树
func NewTrie() *Trie {
	return &Trie{root: &TrieNode{children: make(map[rune]*TrieNode)}}
}

// Insert 插入拼音→词条映射
func (t *Trie) Insert(pinyin string, entry DictEntry) {
	node := t.root
	for _, r := range pinyin {
		if node.children[r] == nil {
			node.children[r] = &TrieNode{children: make(map[rune]*TrieNode)}
		}
		node = node.children[r]
	}
	node.isEnd = true
	node.entries = append(node.entries, entry)
}

// Search 搜索拼音对应的词条
func (t *Trie) Search(pinyin string) []DictEntry {
	node := t.root
	for _, r := range pinyin {
		if node.children[r] == nil {
			return nil
		}
		node = node.children[r]
	}
	if !node.isEnd {
		return nil
	}
	return node.entries
}

// PrefixSearch 前缀搜索（支持简拼）
func (t *Trie) PrefixSearch(prefix string) []DictEntry {
	node := t.root
	for _, r := range prefix {
		if node.children[r] == nil {
			return nil
		}
		node = node.children[r]
	}

	// 收集所有子节点中的词条
	var result []DictEntry
	collectEntries(node, &result)
	return result
}

func collectEntries(node *TrieNode, result *[]DictEntry) {
	if node.isEnd {
		*result = append(*result, node.entries...)
	}
	for _, child := range node.children {
		collectEntries(child, result)
	}
}
