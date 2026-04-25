import math
import win32api
import logging
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import ensure_focus, smooth_move

logger = logging.getLogger("HumanoidSkills")

@skill_handler("human_idle_move")
def human_idle_move(vm: ViewportManager, duration: float = 2.0, steps: int = 30, auto_focus: bool = True, **kwargs):
    """
    V8.1 丝滑拟人化漫游 (基于通用 smooth_move)
    """
    # 1. 前置对焦
    ensure_focus(vm, enabled=auto_focus)
    
    rect = vm.dock_rect
    if not rect: return False
    
    # 2. 生成目标点 (窗口 15%~85% 区域)
    target_x = rect["x"] + random_randint_fixed(int(rect["width"] * 0.15), int(rect["width"] * 0.85))
    target_y = rect["y"] + random_randint_fixed(int(rect["height"] * 0.15), int(rect["height"] * 0.85))
    
    import random
    logger.info(f"[IDLE] 开始丝滑漫游至目标点: ({target_x}, {target_y})")

    # 3. 执行物理滑动
    smooth_move(target_x, target_y, duration=duration, steps=steps)
    
    return True

def random_randint_fixed(a, b):
    import random
    return random.randint(a, b)
