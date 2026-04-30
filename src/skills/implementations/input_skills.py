import time
import random
import pydirectinput
pydirectinput.FAILSAFE = False
import win32api
import win32con
import logging
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import ensure_focus 

# [V12.5] 核心安全补丁：关闭物理边界自杀保护
pydirectinput.FAILSAFE = False

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
    # [V12.0] 终极暴力回顶/触底：50次连发 + 5波物理滚轮冲击
    if auto_focus:
        rect = vm.dock_rect
        if rect:
            # KVM模式下，点中心只移动鼠标，不执行物理点击以防误触
            cx, cy = int(rect["x"] + rect["width"]/2), int(rect["y"] + rect["height"]/2)
            win32api.SetCursorPos((cx, cy))
            time.sleep(0.1)
            
    key = "end" if direction == "end" else "home"
    sub_key = "pagedown" if direction == "end" else "pageup"
    wheel_amount = -20000 if direction == "end" else 20000
    
    logger.info(f"Executing ULTIMATE BRUTE FORCE scroll: {key}")
    
    # 1. 第一重：Ctrl + Home/End (跳转指令)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    pydirectinput.press(key)
    time.sleep(0.1)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    
    time.sleep(0.2)
    
    # 2. 飓风级物理滚轮冲击 (强制渲染引擎清空偏移，绝不误触键盘)
    for _ in range(5):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
        time.sleep(0.05)
        
    return True

@skill_handler("play_bell")
def play_bell(vm: ViewportManager, **kwargs):
    import winsound
    # 播放一个清脆的提示音 (Asterisk 是标准的系统通知音)
    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
    logger.info("Notification bell played.")
    return True

@skill_handler("humanoid_time_equalizer")
def humanoid_time_equalizer(vm: ViewportManager, min_sec=102, max_sec=280, bridge=None, **kwargs):
    if not bridge or not hasattr(bridge, "start_time"):
        logger.warning("No start_time found in bridge, skipping equalizer.")
        return True
        
    elapsed = time.time() - bridge.start_time
    target = random.uniform(min_sec, max_sec)
    
    if elapsed < target:
        wait_time = target - elapsed
        logger.info(f"Humanoid Equalizer: Current {elapsed:.1f}s, Target {target:.1f}s. Waiting {wait_time:.1f}s...")
        time.sleep(wait_time)
    else:
        logger.info(f"Humanoid Equalizer: Already at {elapsed:.1f}s, Target {target:.1f}s. No wait needed.")
        
    return True

class InputSkillsMixin:
    pass
