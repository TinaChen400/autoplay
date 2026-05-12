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
        text = self.extractor.get_window_text(dock_rect)
        if not text:
            return "未能识别到屏幕文字"
        
        # 2. 调用 AI
        return self.engine.chat(text, TRANSLATE_SYSTEM_PROMPT)
