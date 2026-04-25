import time
import win32api
import win32con
import pyautogui
import os
import logging
import re
import cv2
import numpy as np
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager

logger = logging.getLogger("TextSkills")

@skill_handler("click_row_target")
def click_row_target(vm: ViewportManager, keywords: list, target_keyword: str, offset_x=0, offset_y=0, step_id=0, **kwargs):
    """
    [V15.9] 深度交互版：自动避让鼠标 + 模拟人类深按点击。
    """
    rect = vm.dock_rect
    if not rect: return False
    
    win_px, win_py = rect['x'], rect['y']
    logi_w, _ = pyautogui.size()
    phys_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    scale = phys_w / logi_w

    # --- [NEW] 避让逻辑：扫码前先将鼠标移开，防止悬浮窗干扰 ---
    # 移到窗口右上角安全区
    win32api.SetCursorPos((int((win_px + rect['width'] - 20)/scale), int((win_py + 20)/scale)))
    time.sleep(0.2) 

    from src.vision.capture import VisionCapture
    vc = VisionCapture()
    ocr = vc.get_ocr()
    frame_np = vc.capture_dock_region({"x": win_px, "y": win_py, "width": rect['width'], "height": rect['height']})
    
    if frame_np is None: return False
    
    # 高清预处理
    h, w = frame_np.shape[:2]
    upscale = cv2.resize(frame_np, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
    lab = cv2.cvtColor(upscale, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8,8))
    cl = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR)
    
    results = ocr.reader.readtext(enhanced)
    canvas = frame_np.copy()
    
    def clean_text(t):
        return re.sub(r'[^a-zA-Z0-9]', '', t).lower()

    anchor_y = None
    target_clean = clean_text(target_keyword)
    search_keywords = [clean_text(kw) for kw in keywords]
    
    # 1. 扫描锚点
    for (bbox, text, prob) in results:
        p1 = (int(bbox[0][0]/2), int(bbox[0][1]/2))
        p2 = (int(bbox[2][0]/2), int(bbox[2][1]/2))
        text_clean = clean_text(text)
        if anchor_y is None and any(kw in text_clean for kw in search_keywords):
            anchor_y = (p1[1] + p2[1]) / 2
            cv2.rectangle(canvas, p1, p2, (255, 0, 0), 2)

    if anchor_y is None:
        cv2.imwrite(rf"D:\Dev\autoplay\temp\fail_step_{step_id}.jpg", canvas)
        return False

    # 2. 扫描目标
    target_rel_pos = None
    for (bbox, text, prob) in results:
        p1 = (int(bbox[0][0]/2), int(bbox[0][1]/2))
        p2 = (int(bbox[2][0]/2), int(bbox[2][1]/2))
        curr_y = (p1[1] + p2[1]) / 2
        text_clean = clean_text(text)
        
        if target_clean in text_clean and abs(curr_y - anchor_y) < 60:
            target_rel_pos = ((p1[0] + p2[0]) / 2, curr_y)
            cv2.rectangle(canvas, p1, p2, (0, 255, 0), 2)
            break

    if target_rel_pos:
        tx = int((win_px + target_rel_pos[0]) / scale) + offset_x
        ty = int((win_py + target_rel_pos[1]) / scale) + offset_y
        
        # 绘制准星并保存
        cv2.drawMarker(canvas, (int(target_rel_pos[0]), int(target_rel_pos[1])), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.imwrite(rf"D:\Dev\autoplay\temp\result_step_{step_id}.jpg", canvas)
        
        # --- [优化] 深度交互点击 ---
        win32api.SetCursorPos((tx, ty))
        time.sleep(0.05)
        # 模拟按下
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.15) # 稍微加长按下时间，确保浏览器捕获
        # 模拟弹起
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        logger.info(f"[SUCCESS] Step {step_id} 点击完成: ({tx}, {ty})")
        return True
    
    return False

class TextSkillsMixin:
    pass
