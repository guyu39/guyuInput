"""FlashText 词典校正器 — 单次遍历 O(N)"""
import json
import logging
from pathlib import Path
from flashtext import KeywordProcessor

logger = logging.getLogger('guyuInput')


class DictionaryCorrector:
    """基于 FlashText 的关键词替换校正器"""

    def __init__(self, dict_dir: Path = None):
        self._kp = KeywordProcessor(case_sensitive=True)
        self._dict_dir = dict_dir or Path(__file__).parent
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, sections: list[str] | None = None):
        """加载词典。sections=None 则全部加载。"""
        dict_path = self._dict_dir / "zh_dict.json"
        if not dict_path.exists():
            logger.warning(f"词典文件不存在: {dict_path}")
            return

        with open(dict_path, "r", encoding="utf-8") as f:
            all_dict = json.load(f)

        count = 0
        for section_name, mapping in all_dict.items():
            if section_name.startswith("_"):
                continue
            if sections and section_name not in sections:
                continue
            for wrong, correct in mapping.items():
                if wrong.startswith("_"):
                    continue
                self._kp.add_keyword(wrong, correct)
                count += 1

        self._loaded = True
        logger.info(f"词典校正器已加载 {count} 条规则")

    def correct(self, text: str) -> str:
        if not text or not self._loaded:
            return text
        return self._kp.replace_keywords(text)
