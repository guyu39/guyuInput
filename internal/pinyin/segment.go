package pinyin

import "strings"

// 声母表
var initials = []string{
	"b", "p", "m", "f", "d", "t", "n", "l",
	"g", "k", "h", "j", "q", "x",
	"zh", "ch", "sh", "r", "z", "c", "s",
	"y", "w",
}

// 韵母表（按长度从长到短排序，确保最长匹配）
var finals = []string{
	"iang", "iong", "uang",
	"ang", "eng", "ing", "ong",
	"ian", "iao", "uai", "uan", "uai",
	"an", "en", "in", "un",
	"ia", "ie", "iu", "ua", "uo", "ui", "ue", "ve",
	"ai", "ei", "ao", "ou", "er",
	"a", "o", "e", "i", "u", "v",
}

// Segment 拼音音节切分（正向最大匹配）
// "nihao" → ["ni", "hao"]
func Segment(pinyin string) []string {
	var result []string
	i := 0

	for i < len(pinyin) {
		matched := false
		remaining := pinyin[i:]

		// 尝试匹配声母+韵母
		for _, initial := range initials {
			if !strings.HasPrefix(remaining, initial) {
				continue
			}
			afterInit := remaining[len(initial):]
			for _, final := range finals {
				if strings.HasPrefix(afterInit, final) {
					syllable := initial + final
					result = append(result, syllable)
					i += len(syllable)
					matched = true
					break
				}
			}
			if matched {
				break
			}
		}

		// 尝试零声母（直接以韵母开头）
		if !matched {
			for _, final := range finals {
				if strings.HasPrefix(remaining, final) {
					result = append(result, final)
					i += len(final)
					matched = true
					break
				}
			}
		}

		if !matched {
			// 无法切分，保留原样
			result = append(result, remaining)
			break
		}
	}

	return result
}

// JoinSyllables 连接音节为无分隔拼音
func JoinSyllables(syllables []string) string {
	return strings.Join(syllables, "")
}
