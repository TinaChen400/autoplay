import logging
import ctypes
from PyQt6.QtWidgets import QApplication
from .core.engine import AssistantEngine
from .vision.capture import ContextExtractor
from .actions.translator import TranslatorAction
from src.ui.overlay.translation_overlay import TranslationOverlay

logger = logging.getLogger("LocalAssistant.Bridge")

class LocalAIManager:
    """
    本地 AI 助手主管理类 (Bridge)。
    作为外部（如 HUD）与内部模块（Core/Vision）之间的桥梁。
    """
    def __init__(self, overlay=None):
        from .vision.capture import ContextExtractor
        from .core.engine import AssistantEngine
        from src.vision.recognition_expert import RecognitionExpert
        
        # [V22.51] 终极稳定版：恢复核心组件，启用 8B 智慧大脑
        self.expert = RecognitionExpert()
        self.extractor = ContextExtractor(self.expert)
        self.engine = AssistantEngine(model_name="llama3.1:8b")
        self.overlay = overlay
        self.last_result = ""
        self.overlay = None # 延迟初始化，确保在 UI 线程创建
        
        logger.info("LocalAIManager 初始化完成")

    def quick_translate_inplace(self, dock_rect: dict):
        """
        [V22.30] 面板中心模式：专注于翻译、要求与极简答案
        """
        import time
        start_t = time.time()
        
        # 1. 提取文字 (全窗口抓取)
        ocr_start = time.time()
        _, full_text = self.extractor.extract_context(dock_rect)
        ocr_time = time.time() - ocr_start
        
        if not full_text: return "未检测到内容"
        
        # 2. AI 决策 (极端中文化 & 逻辑重组版)
        prompt = """你是一个顶级的协同专家。请对提供的文字进行【深度清洗】和【重组】。
你的目标是产出【纯净的简体中文】报告。

1. 【页面详情翻译】：
(要求：严禁复读 OCR 中的拼写错误。请自动将 "Prway" 纠正为 "隐私"，将 "N2ssag25" 之类的乱码直接剔除。
请直接用一段通顺的中文描述：页面题目是什么？当前是什么任务？核心问题是什么？)

2. 【任务执行建议】：
- 核心目标：(一句话说清目前要做什么)
- 专家推荐：(基于你的分析，建议用户选哪个或怎么填，并给出理由)

3. 【地道英文建议】：
(根据题型直接给出建议。如果是问答题，请提供两段高质量英文：一段回答 Like，一段回答 Dislike)

禁止输出任何多余的开场白，直接给出干货。"""
        # 2. 智能任务感知 (判断是否是新任务)
        import difflib
        
        # 计算与上次任务文字的相似度
        last_text = getattr(self, "last_full_text", "")
        similarity = difflib.SequenceMatcher(None, last_text, full_text).ratio()
        
        # 如果变化超过 50%，判定为新任务，强制重置记忆
        is_new_task = similarity < 0.4
        self.last_full_text = full_text
        
        if is_new_task:
            print(f"[BRIDGE] 检测到任务大幅变更 (相似度: {similarity:.2f})，已重置 AI 会话记忆。")
        else:
            print(f"[BRIDGE] 维持当前任务上下文 (相似度: {similarity:.2f})。")

        ai_start = time.time()
        # 仅在检测到新任务时重置历史
        result = self.engine.chat(full_text, prompt, reset_history=is_new_task)
        ai_time = time.time() - ai_start
        
        # 3. 清理之前的 AR 贴图，保持屏幕整洁
        if self.overlay:
            self.overlay.clear_labels()
            
        total_time = time.time() - start_t
        return f"{result}\\n\\n(总耗时: {total_time:.1f}s | OCR: {ocr_time:.1f}s)"

    def clear_ai_overlay(self):
        """手动清除 AR 覆盖层"""
        if self.overlay:
            self.overlay.clear_labels()
        return "已清除"

    def quick_advice(self, dock_rect: dict) -> str:
        """
        一键获取结构化分析建议 (V22.18)
        """
        from .core.prompts.templates import ADVICE_SYSTEM_PROMPT
        logger.info("执行结构化任务分析...")
        
        # 使用更精准的段落级提取
        _, full_text = self.extractor.extract_context(dock_rect)
        if not full_text: return "未能提取到屏幕文字"
        
        # 调用极速模型
        result = self.engine.chat(full_text, ADVICE_SYSTEM_PROMPT)
        self.last_result = result if result else "AI 分析超时或失败"
        return self.last_result

    def get_status(self) -> dict:
        """返回引擎健康状态"""
        return {
            "online": self.engine.check_health(),
            "model": self.engine.model_name
        }
