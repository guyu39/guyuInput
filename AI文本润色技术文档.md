# AI 文本润色 — 技术文档

## 1. 功能概述

语音识别输出的文本通常存在以下问题：
- 缺少标点符号（离线模型尤为明显）
- 口语化表达、重复、冗余
- 缺乏段落和逻辑结构
- **离线小模型易将专有名词、行业术语识别为同音字**（如 `"图吧"` → `"图巴"`，`"鲲鹏"` → `"昆鹏"`）

本方案采用**二级后处理管线**：

```
ASR 原始文本 → [一级: FlashText 词典校正] → [二级: LLM 润色] → 注入文本
```

| 阶段 | 技术 | 定位 | 延迟 |
|------|------|------|------|
| **一级 — 词典校正** | FlashText 关键词匹配 | 确定性替换，无 LLM 调用 | < 1ms |
| **二级 — AI 润色** | LLM (OpenAI/豆包等) | 语义理解、句式重构 | 1~5s |

一级词典校正解决了小模型"不认识专有名词"的问题；二级 AI 润色解决"口语转书面"的问题。两者独立配置，可单独启用。

### 1.1 AI 润色能力

| 能力 | 说明 | 示例 |
|------|------|------|
| **标点修正** | 自动添加/修正中英文标点 | `今天开会讨论项目进度` → `今天开会，讨论项目进度。` |
| **口语转书面** | 去除口头禅、重复词，转为书面语 | `那个那个我觉得这个方案还行吧` → `我认为该方案可行。` |
| **逻辑重构** | 调整语序，合并短句，拆分长句 | |
| **格式化** | 生成列表、编号、分段 | |
| **多语言翻译** | 识别结果翻译为指定语言 | 中文 → 英文 |

### 1.2 润色强度

用户可选择三种强度（类似 iOS 语音输入）：

| 强度 | 行为 | 适用场景 |
|------|------|---------|
| **仅标点** | 只加标点，不改原文 | 代码注释、精确输入 |
| **适度润色（默认）** | 标点 + 去口语 + 轻度整理 | 日常聊天、邮件 |
| **深度润色** | 完全重写为正式书面语 | 文档、报告、演讲稿 |

---

## 2. 架构设计

### 2.1 在现有流程中的位置

```
                      ┌─────────────┐
                      │  ASR 识别    │
                      │ (在线/离线)  │
                      └──────┬──────┘
                             │ raw_text
                             ▼
                  ┌─────────────────────┐
                  │  一级: 词典校正      │  ← FlashText, < 1ms
                  │  (可选, 默认开启)    │
                  └──────────┬──────────┘
                             │ corrected_text
                             ▼
                  ┌─────────────────────┐
                  │  二级: AI 润色       │  ← LLM 异步请求, 1~5s
                  │  (可选, 默认关闭)    │
                  └──────────┬──────────┘
                             │ polished_text (or corrected_text on failure)
                             ▼
                      ┌─────────────┐
                      │  文本注入    │
                      │  Ctrl+V     │
                      └─────────────┘
```

### 2.2 模块划分

```
backend/
├── dictionary/              ← 新增: 一级词典校正
│   ├── __init__.py
│   ├── corrector.py         # FlashText 封装
│   └── zh_dict.json         # 默认中文词典
└── polish/                  ← 新增: 二级 AI 润色
    ├── __init__.py
    ├── base.py              # 抽象基类
    ├── openai.py            # OpenAI / 兼容 API
    ├── doubao.py            # 豆包 (ark.cn)
    ├── dispatcher.py        # 润色调度器
    └── prompts.py           # Prompt 模板
```

### 2.3 交互流程

```
stop_recording()
  │
  ├─ 1. ASR 识别完成 → raw_text
  │
  ├─ 2. 一级词典校正（若启用）:
  │     └─ FlashText 单次遍历替换 → corrected_text (< 1ms)
  │
  ├─ 3. 二级 AI 润色（若启用）:
  │     ├─ asr_partial.emit("润色中...")
  │     ├─ QApplication.processEvents()  ← 刷新 UI
  │     ├─ 异步调用 LLM
  │     ├─ 成功 → polished_text
  │     └─ 失败 → 降级使用 corrected_text
  │
  ├─ 4. 若两级均禁用 → 直接注入 raw_text（与当前行为一致）
  │
  └─ 5. 注入最终文本
```

---

## 3. FlashText 离线词典校正

### 3.1 背景与动机

离线 ASR 模型（如 SenseVoice INT8，~239MB）为了控制体积和推理成本，牺牲了广阔的领域知识。实际使用中常见以下问题：

| 错误类型 | 原始识别 | 期望结果 |
|----------|---------|---------|
| 专有名词 | `"图巴"` | `"图吧"` |
| 行业术语 | `"云原生"` 识别为 `"云元生"` | `"云原生"` |
| 人名 | `"张雪峰"` → `"张学峰"` | `"张雪峰"` |
| 品牌名 | `"字节跳动"` → `"自洁跳动"` | `"字节跳动"` |
| 缩写/代码 | `"K8s"` → `"k 八 s"` | `"K8s"` |

在线大模型可以靠上下文理解纠正这类错误，但离线小模型缺乏这种能力。**词典校正**通过维护一个"易错词 → 正确词"的映射表，在识别完成后做一次确定性替换。

### 3.2 为什么选 FlashText

FlashText 是 2017 年由 Vikash Singh 提出的关键词查找/替换算法，发表于 AAAI 2018。核心特性：

- **单次遍历**：在输入文本上只做一次扫描，同时匹配/替换所有关键词
- **O(N) 时间复杂度**：N = 输入文本长度，与词典大小**完全无关**
- **无回溯**：基于 Trie 的 Aho-Corasick 变体，找到匹配立即替换，不回溯
- **词典规模无关**：10 个词和 10,000 个词的查找耗时几乎相同

对比传统方案：

| 方案 | 100 词词典耗时 | 10,000 词词典耗时 | 复杂度 |
|------|-------------|----------------|--------|
| 逐条 `str.replace()` | ~5ms | ~500ms | O(D × N) |
| 正则表达式 `re.sub()` | ~3ms | ~300ms | O(D × N) |
| **FlashText** | **< 0.5ms** | **< 0.5ms** | **O(N)** |

对于语音输入法的后处理场景，用户对延迟极为敏感。FlashText 保证了无论词典多大，校正耗时都控制在 1ms 以内。

### 3.3 词典格式

使用 JSON 文件存储，键为"易错的识别结果"，值为"正确的文本"。按领域分 section：

```json
{
  "tech": {
    "_desc": "技术术语",
    "云元生": "云原生",
    "k八s": "K8s",
    "k 八 s": "K8s",
    "戴文": "DevOps",
    "围补服务": "微服务",
    "容器花": "容器化",
    "cicd": "CI/CD",
    "ap i": "API",
    "sdk": "SDK",
    "贾瓦": "Java",
    "皮松": "Python"
  },
  "brand": {
    "_desc": "品牌/产品名",
    "自洁跳动": "字节跳动",
    "字杰": "字节",
    "阿里吧吧": "阿里巴巴",
    "腾训": "腾讯",
    "华威": "华为",
    "鲲鹏": "鲲鹏",
    "昆鹏": "鲲鹏",
    "通易千问": "通义千问",
    "文新一言": "文心一言"
  },
  "people": {
    "_desc": "常见人名",
    "周红衣": "周鸿祎",
    "雷君": "雷军",
    "张一明": "张一鸣",
    "马斯可": "马斯克"
  },
  "general": {
    "_desc": "通用纠错",
    "图巴": "图吧",
    "固雨": "谷雨"
  }
}
```

**设计要点**：
- 键是**模型实际输出的错误文本**，不是正确文本的变体枚举
- 按领域分 section 便于用户按需启用/禁用
- `_desc` 字段仅注释，校正器忽略
- 用户可自行添加自定义词典文件（设置面板提供导入入口）

### 3.4 校正器实现

```python
# backend/dictionary/corrector.py

import json
from pathlib import Path
from flashtext import KeywordProcessor


class DictionaryCorrector:
    """基于 FlashText 的词典校正器 — 单次遍历 O(N)"""

    def __init__(self, dict_dir: Path = None):
        self._kp = KeywordProcessor(case_sensitive=True)
        self._dict_dir = dict_dir or Path(__file__).parent

    def load(self, sections: list[str] | None = None):
        """加载词典。sections=None 则全部加载。"""
        dict_path = self._dict_dir / "zh_dict.json"
        with open(dict_path, "r", encoding="utf-8") as f:
            all_dict = json.load(f)

        for section_name, mapping in all_dict.items():
            if section_name.startswith("_"):
                continue
            if sections and section_name not in sections:
                continue
            for wrong, correct in mapping.items():
                if not wrong.startswith("_"):
                    self._kp.add_keyword(wrong, correct)

    def correct(self, text: str) -> str:
        return self._kp.replace_keywords(text) if text else text
```

**使用示例**：

```python
corrector = DictionaryCorrector()
corrector.load()  # 加载全部词典
corrected = corrector.correct("我们使用 k 八 s 实现容器花")
# → "我们使用 K8s 实现容器化"
```

### 3.5 与 AI 润色的关系

词典校正和 AI 润色是**互补**而非替代：

| 维度 | 词典校正 | AI 润色 |
|------|---------|--------|
| 原理 | 确定性字符串替换 | LLM 语义理解 |
| 延迟 | < 1ms | 1~5s |
| 网络依赖 | 无 | 需要 |
| 专有名词 | 强（用户自定义词典） | 中（依赖模型训练数据） |
| 口语转书面 | 不支持 | 支持 |
| 标点修正 | 不支持 | 支持 |

推荐组合：**词典校正始终开启**（零成本），AI 润色按需启用。

---

## 4. LLM 供应商接入

### 4.1 OpenAI（及兼容 API）

```python
class OpenAIPolisher(BasePolisher):
    """OpenAI / 兼容 API (如 deepseek, moonshot 等)"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def polish(self, text: str, mode: PolishMode) -> str:
        # POST {base_url}/chat/completions
        # Body: { model, messages: [system_prompt, user_text] }
```

### 4.2 豆包 (火山引擎 ark)

```python
class DoubaoPolisher(BasePolisher):
    """豆包大模型 (ark.cn-beijing.volces.com)"""

    def __init__(self, api_key: str, model: str = "doubao-pro-32k"):
        self.endpoint = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
```

### 4.3 供应商对比

| 供应商 | API 兼容 | 延迟 | 成本 | 备注 |
|--------|---------|------|------|------|
| OpenAI | OpenAI 原生 | ~1-3s | $$ | gpt-4o-mini 性价比高 |
| 豆包 | OpenAI 兼容 | ~1-2s | ¥ | 国内访问快 |
| DeepSeek | OpenAI 兼容 | ~2-4s | ¥ | 中文效果好 |
| 阿里通义 | OpenAI 兼容 | ~1-3s | ¥ | 有免费额度 |

---

## 5. Prompt 设计

### 5.1 仅标点

```
你是一个标点修正工具。请为以下语音识别文本添加合适的标点符号，
不要修改任何词语和语序，只加标点。

输入：{text}
输出：
```

### 5.2 适度润色（默认）

```
你是专业的文字润色助手。请润色以下语音识别文本：

规则：
1. 添加合适的标点符号
2. 去除"嗯、啊、那个"等口头禅
3. 修正明显的语法错误
4. 保持原意和口语风格，不要改成过于正式的书面语
5. 直接输出润色后的文本，不要解释

输入：{text}
输出：
```

### 5.3 深度润色

```
你是专业的文字编辑。请将以下语音识别文本改写为正式书面表达：

规则：
1. 添加完整的标点符号
2. 去除口语化表达和冗余
3. 调整语序使其符合书面逻辑
4. 适当分段（如有必要）
5. 直接输出改写后的文本，不要解释

输入：{text}
输出：
```

---

## 6. UI 设计

### 6.1 录音条状态扩展

在润色模式下，录音条的状态变化：

```
按住说话 → "正在聆听..."
    ↓
松开热键 → "识别中..."
    ↓
词典校正 → (无感知, < 1ms)
    ↓
ASR 完成 → "润色中..."  (仅 AI 润色启用时)
    ↓
润色完成 → 显示润色后文本（可预览 1-2 秒）
    ↓
注入 → 切换回 idle
```

### 6.2 设置面板新增区域

在现有设置面板底部新增「文本后处理」卡片：

```
┌─────────────────────────────────────┐
│  文本后处理                          │
│  ─────────────────────────────────  │
│  词典校正        [✓ 启用]            │
│  自定义词典      [导入 JSON...]      │
│  ─────────────────────────────────  │
│  AI 润色         [开关]              │
│  供应商          [OpenAI ▼]          │
│  API Key         [············]      │
│  模型            [gpt-4o-mini ▼]     │
│  自定义 URL      [              ]    │
│  润色强度        ○ 仅标点            │
│                 ● 适度润色           │
│                 ○ 深度润色           │
└─────────────────────────────────────┘
```

### 6.3 配置存储（config.db）

```sql
-- 词典校正
INSERT INTO config VALUES ('dictionary_enabled', 'true');
INSERT INTO config VALUES ('dictionary_sections', '["tech","brand","people","general"]');

-- AI 润色
INSERT INTO config VALUES ('polish_enabled', 'false');
INSERT INTO config VALUES ('polish_provider', 'openai');
INSERT INTO config VALUES ('polish_api_key', '');
INSERT INTO config VALUES ('polish_model', 'gpt-4o-mini');
INSERT INTO config VALUES ('polish_base_url', '');
INSERT INTO config VALUES ('polish_mode', 'moderate');
```

---

## 7. 实现计划

### 7.1 PR 拆分

| PR | 内容 | 预计文件数 |
|----|------|-----------|
| PR1 | `backend/dictionary/` — FlashText 词典校正器 + 默认词典 | 3 |
| PR2 | `backend/polish/` 基础架构：抽象基类 + Prompts | 3 |
| PR3 | OpenAI 润色器实现 | 1 |
| PR4 | 豆包润色器实现 | 1 |
| PR5 | 润色调度器 + app.py 集成（含词典校正调用） | 4 |
| PR6 | 设置面板 UI：词典校正 + AI 润色配置 | 2 |
| PR7 | 润色模式选择 + 自定义 API URL | 2 |

### 7.2 核心代码量估算

| 模块 | 行数 |
|------|------|
| `backend/dictionary/corrector.py` | ~40 |
| `backend/dictionary/zh_dict.json` | ~80 |
| `backend/polish/base.py` | ~30 |
| `backend/polish/prompts.py` | ~40 |
| `backend/polish/openai.py` | ~60 |
| `backend/polish/doubao.py` | ~50 |
| `backend/polish/dispatcher.py` | ~50 |
| `backend/app.py`（集成） | +25 |
| `ui/settings_page.py`（UI） | +80 |

---

## 8. 风险与边界

| 风险 | 应对 |
|------|------|
| 词典过度替换 | FlashText 区分大小写 + 全词匹配；长词优先匹配，避免短词误伤 |
| LLM 响应慢 (>5s) | 设置 5 秒超时，超时降级用校正后文本 |
| API 调用失败 | 捕获异常，降级用校正后文本 + 日志告警 |
| API Key 泄露 | 仅存储在本地 config.db，不联网传输 |
| 润色后语义偏离 | 仅标点模式几乎无风险；深度模式在 UI 提示用户 |
| 离线 + 润色冲突 | 合理场景：离线识别 + 词典校正（本地）+ 在线润色；纯离线仅校正 |
| 成本 | gpt-4o-mini 每次润色约 \$0.0001（~200 token） |
| 用户感知延迟 | UI 明确展示 "润色中..."，管理预期 |

---

*文档生成日期：2026-05-24*
*针对 guyuInput 项目定制*
