import logging
from .core.engine import AssistantEngine
from .vision.capture import ContextExtractor
from .actions.translator import TranslatorAction

logger = logging.getLogger("LocalAssistant.Bridge")

class LocalAIManager:
    """
    本地 AI 助手主管理类 (Bridge)。
    作为外部（如 HUD）与内部模块（Core/Vision）之间的桥梁。
    """
    def __init__(self, model_name: str = "llama3.1:8b"):
        self.engine = AssistantEngine(model_name=model_name)
        self.extractor = ContextExtractor()
        
        # 初始化具体动作
        self.translator = TranslatorAction(self.engine, self.extractor)
        
        self.last_result = ""
        logger.info("LocalAIManager 初始化完成")

    def quick_translate(self, dock_rect: dict) -> str:
        """
        一键翻译当前窗口内容。
        """
        logger.info("执行一键翻译...")
        result = self.translator.run(dock_rect)
        self.last_result = result if result else "翻译失败"
        return self.last_result

    def quick_advice(self, dock_rect: dict) -> str:
        """
        一键获取逻辑建议。
        """
        from .core.prompts.templates import ADVISOR_SYSTEM_PROMPT
        logger.info("执行逻辑分析...")
        text = self.extractor.get_window_text(dock_rect)
        if not text: return "未能提取到上下文"
        
        result = self.engine.chat(text, ADVISOR_SYSTEM_PROMPT)
        self.last_result = result if result else "分析失败"
        return self.last_result

    def get_status(self) -> dict:
        """返回引擎健康状态"""
        return {
            "online": self.engine.check_health(),
            "model": self.engine.model_name
        }
