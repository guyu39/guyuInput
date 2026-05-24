"""润色 Prompt 模板"""
from .base import PolishMode

SYSTEM_PROMPTS = {
    PolishMode.LIGHT: (
        "你是一个标点修正工具。请为以下语音识别文本添加合适的标点符号，"
        "不要修改任何词语和语序，只加标点。"
    ),
    PolishMode.MODERATE: (
        "你是专业的文字润色助手。请润色以下语音识别文本。\n\n"
        "规则：\n"
        "1. 添加合适的标点符号\n"
        '2. 去除"嗯、啊、那个"等口头禅\n'
        "3. 修正明显的语法错误\n"
        "4. 保持原意和口语风格，不要改成过于正式的书面语\n"
        "5. 直接输出润色后的文本，不要解释"
    ),
    PolishMode.DEEP: (
        "你是专业的文字编辑。请将以下语音识别文本改写为正式书面表达。\n\n"
        "规则：\n"
        "1. 添加完整的标点符号\n"
        "2. 去除口语化表达和冗余\n"
        "3. 调整语序使其符合书面逻辑\n"
        "4. 适当分段（如有必要）\n"
        "5. 直接输出改写后的文本，不要解释"
    ),
}


def get_prompt(text: str, mode: PolishMode) -> str:
    return f"{SYSTEM_PROMPTS[mode]}\n\n输入：{text}\n输出："
