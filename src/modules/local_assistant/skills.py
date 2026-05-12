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
    if not rect: return False
    
    result = manager.quick_translate(rect)
    # [V22.5] 将结果存入 ViewportManager，以便 UI 渲染
    # 假设 vm 有一个可以存储临时状态的地方，或者我们直接通过 log 返回
    print(f"[AI-RESULT] {result}")
    return True

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
    return True
