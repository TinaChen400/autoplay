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

        # 2. 动态比例计算与对位
        logi_w, _ = pyautogui.size()
        full_screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        scale = full_screen_w / logi_w
        
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
        import random
        scrolls = kwargs.get("scroll_amount", [2, 4])
        count = random.randint(scrolls[0], scrolls[1])
        for i in range(count):
            pyautogui.scroll(120) 
            time.sleep(0.3)
        return True
