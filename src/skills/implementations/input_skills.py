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
    ensure_focus(vm, enabled=auto_focus)
    key = "end" if direction == "end" else "home"
    pydirectinput.press(key)
    return True

class InputSkillsMixin:
    pass
