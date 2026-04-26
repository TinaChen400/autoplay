import time
import win32api
import win32con
import pyautogui
import os
from src.skills.humanize import smooth_move

class VisualSkillsMixin:
    """
    [V14.0] 极简快准版：去冗余、快响应、深穿透。
    """
    
    def click_landmark(self, keywords, offset_x=0, offset_y=0, **kwargs):
        """
        极简视觉点击：识别后瞬间打击。
        """
        import cv2
        import numpy as np
        
        # 1. 获取物理原点与快照
        rect = self.wm.get_window_rect()
        win_px, win_py = rect['left'], rect['top']
        
        from src.vision.capture import VisionCapture
        vc = VisionCapture()
        ocr = vc.get_ocr()
        frame_np = vc.capture_dock_region({"x": win_px, "y": win_py, "width": rect['width'], "height": rect['height']})
        
        found_pos = None
        if frame_np is not None:
            for kw in keywords:
                found_pos = ocr.find_largest_element(frame_np, kw)
                if found_pos: break
        
        if not found_pos:
            return False

        # 获取逻辑分辨率和物理分辨率的比例
        logi_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        phys_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN) # 这里通常是一致的，或者通过 GetSystemMetrics 获取
        scale = 1.0 # 巡航内部采用逻辑坐标
        
        target_x = int((win_px + found_pos[0]) / scale) + offset_x
        target_y = int((win_py + found_pos[1]) / scale) + offset_y
        
        # 3. 瞬间执行 (驱动级)
        win32api.SetCursorPos((target_x, target_y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        self._log(f"[HIT] 已点击锚点下方 {offset_y}px: ({target_x}, {target_y})")
        return True

    def zoom_pan_cruise(self, keywords, **kwargs):
        """
        [V14.1] 暴力巡航引擎：锚点锁定 + 视觉缩放 + 物理平移。
        """
        # 1. 尝试锁定图片锚点并激活放大视图
        self._log(f"正在启动暴力巡航，目标关键词: {keywords}")
        if not self.click_landmark(keywords, offset_y=80): # 点击锚点下方进入图片区
            self._log("未找到巡航锚点，将在当前位置执行盲巡...")
        
        time.sleep(0.5)
        
        # 2. 获取平移参数
        import random
        scroll_range = kwargs.get("scroll_amount", [3, 6])
        pan_dx = kwargs.get("pan_dx", 60)
        pan_dy = kwargs.get("pan_dy", 40)
        
        # 3. 执行巡航序列
        steps = random.randint(scroll_range[0], scroll_range[1])
        for i in range(steps):
            # 随机滚轮 (缩放)
            scroll_val = random.choice([120, -120, 240])
            # [V17.3] 换用 Win API 滚动，彻底避开 FailSafe 崩溃
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, scroll_val, 0)
            
            # 物理平移 (模拟拖动或视觉晃动)
            # [V14.2] 修复：取绝对值确保随机区间合法
            safe_dx = abs(pan_dx)
            safe_dy = abs(pan_dy)
            dx = random.randint(-safe_dx, safe_dx)
            dy = random.randint(-safe_dy, safe_dy)
            
            # 使用驱动级相对移动
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)
            
            time.sleep(random.uniform(0.3, 0.6))
            
        self._log(f"巡航完成，共执行 {steps} 组视觉偏移操作。")
        return True
