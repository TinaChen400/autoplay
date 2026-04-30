import math
import win32api
import logging
import random
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import ensure_focus, smooth_move

logger = logging.getLogger("HumanoidSkills")

def _parse_val(val):
    if isinstance(val, (int, float)): return float(val)
    if "-" in str(val):
        parts = str(val).split("-")
        return random.uniform(float(parts[0]), float(parts[1]))
    return float(val)

@skill_handler("human_idle_move")
def human_idle_move(vm: ViewportManager, duration: float = 2.0, steps: int = 30, auto_focus: bool = True, **kwargs):
    """
    V8.2 丝滑拟人化漫游 (已修复随机时长解析)
    """
    ensure_focus(vm, enabled=auto_focus)
    rect = vm.dock_rect
    if not rect: return False
    
    # 动态解析时长
    final_duration = _parse_val(duration)
    
    # 生成目标点 (窗口 15%~85% 区域)
    target_x = rect["x"] + random.randint(int(rect["width"] * 0.15), int(rect["width"] * 0.85))
    target_y = rect["y"] + random.randint(int(rect["height"] * 0.15), int(rect["height"] * 0.85))
    
    logger.info(f"[IDLE] 拟人化漫游开始: ({target_x}, {target_y}) 预计耗时: {final_duration:.1f}s")

    # 执行物理滑动
    smooth_move(target_x, target_y, duration=final_duration, steps=steps)
    
    return True
