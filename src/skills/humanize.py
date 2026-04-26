# -*- coding: utf-8 -*-
import math
import time
import random
import win32api
import win32con
import logging
from src.core.viewport import ViewportManager

logger = logging.getLogger("Humanize")

def random_delay(min_sec: float = 0.2, max_sec: float = 0.8):
    """模拟人类执行动作前的微小迟疑"""
    time.sleep(random.uniform(min_sec, max_sec))

def ensure_focus(vm: ViewportManager, enabled=True):
    """
    [V13.0] 恢复版：配合 JSON 精细化控制，确保关键步骤（如退出巡航、一键触底）能拿回焦点。
    """
    if not enabled: return
    rect = vm.dock_rect
    if rect:
        # [V17.3] 换用原生 Win API 点击，确保全局驱动一致
        rx = rect["x"] + int(rect["width"] * 0.9)
        ry = rect["y"] + int(rect["height"] * 0.5)
        
        win32api.SetCursorPos((rx, ry))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        time.sleep(0.5)
        logger.info(f"[HUMAN] 稳健对焦点击 (WinAPI): ({rx}, {ry})")

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

def human_jitter(target_x, target_y, intensity=4):
    """
    [V10.1] 模拟人手点击前的微小对准和颤动。
    """
    import random, time, win32api
    for _ in range(3):
        jx = target_x + random.randint(-intensity, intensity)
        jy = target_y + random.randint(-intensity, intensity)
        win32api.SetCursorPos((jx, jy))
        time.sleep(random.uniform(0.05, 0.1))
    # 最终归位
    win32api.SetCursorPos((target_x, target_y))

def decision_hesitation(min_sec=0.5, max_sec=2.0):
    """
    [V10.2] 模拟填表时看着选项思考的停顿。
    """
    import time, random
    # 30% 概率会多停顿一会儿
    wait = random.uniform(min_sec, max_sec)
    if random.random() < 0.3:
        wait += random.uniform(1.0, 3.0)
    time.sleep(wait)
