from ..vision.capture import ContextExtractor
from ..core.engine import AssistantEngine
from ..core.prompts.templates import TRANSLATE_SYSTEM_PROMPT

class TranslatorAction:
    """翻译动作编排"""
    def __init__(self, engine: AssistantEngine, extractor: ContextExtractor):
        self.engine = engine
        self.extractor = extractor

    def run(self, dock_rect: dict) -> str:
        # 1. 提取文字
        _, text = self.extractor.extract_context(dock_rect)
        if not text:
            return "未能识别到屏幕文字"
        
        # 2. 调用 AI
        return self.engine.chat(text, TRANSLATE_SYSTEM_PROMPT)

    def run_fast(self, text: str) -> str:
        """极速翻译模式：仅返回译文"""
        prompt = f"你是一个极其忠实的翻译助手。请将以下内容翻译成中文。\n规则：\n1. 必须翻译出每一个单词和细节，严禁任何形式的省略、简化或总结。\n2. 保持行对应。\n3. 如果内容不连贯，请尽可能根据单词意思还原翻译。\n\n待翻译内容：\n{text}"
        return self.engine.chat(text, prompt)
