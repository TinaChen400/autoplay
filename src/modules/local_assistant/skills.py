# -*- coding: utf-8 -*-
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from .bridge import LocalAIManager

# 懒加载 Manager，避免启动时即初始化 AI 引擎
_ai_manager = None

def get_ai_manager():
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = LocalAIManager()
    return _ai_manager

@skill_handler("local_ai_translate")
def local_ai_translate(vm: ViewportManager, **kwargs) -> bool:
    """
    [Local AI] 自动提取当前窗口文字并翻译。
    结果将通过 ViewportManager 或日志反馈至 HUD。
    """
    manager = get_ai_manager()
    rect = vm.dock_rect
    if not rect:
        # [V22.9] 暴力调试模式：未对位时强制抓取全屏
        print("[AI-DEBUG] 未发现对位窗口，使用全屏调试模式...")
        rect = {"x": 0, "y": 0, "width": 1920, "height": 1080}
    
    result = manager.quick_translate_inplace(rect)
    print(f"[AI-RESULT] {result}")
    return result 

@skill_handler("local_ai_clear")
def local_ai_clear(vm: ViewportManager, **kwargs) -> bool:
    manager = get_ai_manager()
    return manager.clear_ai_overlay()

@skill_handler("local_ai_advice")
def local_ai_advice(vm: ViewportManager, **kwargs) -> bool:
    """
    [Local AI] 自动分析上下文并给出建议。
    """
    manager = get_ai_manager()
    rect = vm.dock_rect
    if not rect: return False
    
    result = manager.quick_advice(rect)
    print(f"[AI-RESULT] {result}")
    return result # 返回字符串，将被 Bridge 捕获
