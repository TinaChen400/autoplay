# -*- coding: utf-8 -*-
import math
import time
import random
import win32api
import logging
from src.core.viewport import ViewportManager

logger = logging.getLogger("Humanize")

def random_delay(min_sec: float = 0.2, max_sec: float = 0.8):
    """模拟人类执行动作前的微小迟疑"""
    time.sleep(random.uniform(min_sec, max_sec))

def ensure_focus(vm: ViewportManager, enabled=True):
    """全局拟人化对焦：在窗口右侧安全区执行一次物理点击"""
    if not enabled: return
    rect = vm.dock_rect
    if rect:
        # [V9.6] 在窗口右侧边缘 (85%-95%) 且垂直中部随机点一下
        rx = rect["x"] + random.randint(int(rect["width"] * 0.85), int(rect["width"] * 0.95))
        ry = rect["y"] + random.randint(int(rect["height"] * 0.3), int(rect["height"] * 0.7))
        
        # 物理移动并点击
        import pyautogui
        pyautogui.click(rx, ry)
        time.sleep(random.uniform(0.1, 0.2))
        logger.info(f"[HUMAN] 自动对焦安全点击: ({rx}, {ry})")

def smooth_move(target_x, target_y, duration=0.6, steps=25):
    """
    [V9.0] 弧线变速移动 (Bezier Curve + Sine Easing)
    比直线滑动更像真人。
    """
    start_x, start_y = win32api.GetCursorPos()
    dist = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
    if dist < 50: # 太近了直接过去
        win32api.SetCursorPos((target_x, target_y))
        return

    # 随机生成一个中转控制点，产生弧度
    # 偏移量约为距离的 10%-20%
    offset = dist * random.uniform(0.1, 0.2)
    angle = math.atan2(target_y - start_y, target_x - start_x) + math.pi/2
    control_x = (start_x + target_x) / 2 + math.cos(angle) * offset * random.choice([-1, 1])
    control_y = (start_y + target_y) / 2 + math.sin(angle) * offset * random.choice([-1, 1])

    for i in range(steps):
        t = (i + 1) / steps
        # 正弦变速 (Easing)
        smooth_t = 0.5 * (1 - math.cos(math.pi * t))
        
        # 二次贝塞尔曲线公式: (1-t)^2*P0 + 2*t*(1-t)*P1 + t^2*P2
        curr_x = int((1-smooth_t)**2 * start_x + 2*smooth_t*(1-smooth_t) * control_x + smooth_t**2 * target_x)
        curr_y = int((1-smooth_t)**2 * start_y + 2*smooth_t*(1-smooth_t) * control_y + smooth_t**2 * target_y)
        
        win32api.SetCursorPos((curr_x, curr_y))
        # 随机抖动延迟
        time.sleep((duration / steps) * random.uniform(0.8, 1.2))
