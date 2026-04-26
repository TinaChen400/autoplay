import time
import random
import pydirectinput
import win32api
import win32con
import logging
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import ensure_focus # <--- 引用统一工具

logger = logging.getLogger("InputSkills")

def _parse_range(range_str):
    if isinstance(range_str, (int, float)):
        return float(range_str)
    if "-" in str(range_str):
        parts = str(range_str).split("-")
        return random.uniform(float(parts[0]), float(parts[1]))
    return float(range_str)

@skill_handler("press_keys")
def press_keys(vm: ViewportManager, keys, interval=0.5, auto_focus=False, **kwargs):
    ensure_focus(vm, enabled=auto_focus)
    logger.info(f"Executing press_keys: {keys}")
    for key in keys:
        pydirectinput.press(key)
        time.sleep(_parse_range(interval))
    return True

@skill_handler("sleep")
def sleep(vm: ViewportManager, seconds=1.0, **kwargs):
    duration = _parse_range(seconds)
    time.sleep(duration)
    return True

@skill_handler("human_scroll")
def human_scroll(vm: ViewportManager, distance=400, steps=5, auto_focus=False, **kwargs):
    ensure_focus(vm, enabled=auto_focus)
    for i in range(steps):
        amount = - (distance // steps)
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
        time.sleep(random.uniform(0.1, 0.2))
    return True

@skill_handler("scroll_home_end")
def scroll_home_end(vm: ViewportManager, direction="end", auto_focus=False, **kwargs):
    # [V10.5] 暴力触底：中心激活 + 多重按键 + 物理滚轮
    if auto_focus:
        rect = vm.dock_rect
        if rect:
            # 点中心，确保主容器获取焦点
            cx, cy = int(rect["x"] + rect["width"]/2), int(rect["y"] + rect["height"]/2)
            win32api.SetCursorPos((cx, cy))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.3)
            
    key = "end" if direction == "end" else "home"
    logger.info(f"Executing BRUTE FORCE scroll: {key}")
    
    # 1. 组合拳：Ctrl + End (强制跳转文档最末尾)
    if direction == "end":
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        pydirectinput.press("end")
        time.sleep(0.1)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    else:
        pydirectinput.press("home")
    
    time.sleep(0.3)
    
    # 2. 超级补位：20 次 PageDown 连击
    if direction == "end":
        for _ in range(20):
            pydirectinput.press("pagedown")
            time.sleep(0.05)
        # 3. 飓风级滚轮：-20000 像素
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -20000, 0)
        
    time.sleep(0.5)
    return True

class InputSkillsMixin:
    pass
