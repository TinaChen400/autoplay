# -*- coding: utf-8 -*-
import os
import time
import cv2
import numpy as np
import difflib
import logging
import win32api
import win32con
import win32gui
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import smooth_move

logger = logging.getLogger("AtomicSkills")

def get_agent():
    # 模拟获取 agent 实例
    class MockAgent:
        def __init__(self):
            self.records_dir = r"D:\Dev\autoplay\records"
            from src.vision.ocr_reader import OCRReader
            from src.vision.capture import VisionCapture
            self.vc = VisionCapture()
    return MockAgent()

# [V7.40] 共享 Oracle 实例，确保图片队列在步骤间持久化
_shared_oracle = None

def get_oracle():
    global _shared_oracle
    if _shared_oracle is None:
        from src.ai.oracle import GPTOracle
        _shared_oracle = GPTOracle()
    return _shared_oracle

@skill_handler("click_grid_cell")
def click_grid_cell(vm: ViewportManager, row_keywords: list, col_keywords: list, **kwargs) -> bool:
    """
    行列网格点击：通过地标词根锁定行 (Y)，通过全局偏移锁定列 (X)。
    """
    agent = get_agent()
    rect = vm.dock_rect
    if not rect: return False

    # 1. 抓取当前视野并识别文字
    view_path = agent.vc.capture_screen(region={"top": int(rect["y"]), "left": int(rect["x"]), "width": int(rect["width"]), "height": int(rect["height"])})
    img = cv2.imread(view_path)
    ocr = agent.vc.get_ocr()
    results = ocr.read_screen(img)
    
    row_y = None
    row_x_base = None
    fuzzy_map = {
        "visual quality": "visual quality",
        "overall preference": "overall preference",
        "instruction following": "instruction follow",
        "content preservation": "content",
        "id preservation": "id"
    }
    
    target_token = fuzzy_map.get(row_keywords[0].lower(), row_keywords[0].lower()[:8])

    for (bbox, text, prob) in results:
        text_clean = text.lower().strip()
        center_y = int((bbox[0][1] + bbox[2][1]) / 2)
        
        # 排除页头干扰 (Y < 300)
        if center_y < 300: continue
        
        if target_token in text_clean:
            row_y = center_y
            row_x_base = bbox[0][0] 
            logger.info(f"Matched row '{text_clean}' by token '{target_token}' at Y={row_y}")
            break
    
    if row_y is None:
        logger.error(f"Skill [click_grid_cell]: Could not find token '{target_token}' in OCR results.")
        return False

    # 2. 全局列中心 X 坐标
    global_col_x = {
        "response a": 750,
        "response b": 815,
        "both good": 885,
        "both bad": 955
    }
    
    target_pos = None
    kw_lower = col_keywords[0].lower()
    
    if kw_lower in global_col_x:
        target_pos = (global_col_x[kw_lower], row_y)
        logger.info(f"Global mapping: Clicking {kw_lower} at X={target_pos[0]}, Y={target_pos[1]}")

    if not target_pos:
        logger.error(f"Skill [click_grid_cell]: Global mapping failed for {col_keywords}")
        return False

    # 绘制验证
    cv2.line(img, (0, row_y), (img.shape[1], row_y), (255, 255, 0), 1)
    cv2.circle(img, target_pos, 10, (255, 0, 0), -1)
    cv2.imwrite(os.path.join(agent.records_dir, "click_verification.jpg"), img)

    # 执行物理点击 (带丝滑滑动)
    smooth_move(int(rect["x"] + target_pos[0]), int(rect["y"] + target_pos[1]), duration=0.4)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return True

@skill_handler("apply_scoring_results")
def apply_scoring_results(vm: ViewportManager, decisions: dict, **kwargs) -> bool:
    """批量评分决策应用"""
    dimension_map = {
        "Overall Preference": ["Overall Preference"],
        "Instruction Following": ["Instruction Following"],
        "ID Preservation": ["ID Preservation"],
        "Content Preservation": ["Content Preservation"],
        "Visual Quality": ["Visual Quality"],
        "Less AI Generated": ["Less AI Generated"]
    }
    for dim, choice in decisions.items():
        if dim in dimension_map:
            click_grid_cell(vm, row_keywords=dimension_map[dim], col_keywords=[choice])
            time.sleep(0.5)
    
    # 自动提交
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -300, 0)
    time.sleep(0.5)
    find_and_click(vm, keywords=["Submit Vote", "Submit"], offset_y=0)
    return True

@skill_handler("lock_window_position")
def lock_window_position(vm: ViewportManager, x: int = 10, y: int = 10, width: int = 1440, height: int = 900, **kwargs) -> bool:
    from src.drivers.window import WindowLock
    locker = WindowLock("Tina")
    success = locker.lock_and_align(x, y, width, height)
    if success: vm.update_dock_rect({"x": x, "y": y, "width": width, "height": height})
    return success

@skill_handler("ai_clear")
def ai_clear_skill(vm: ViewportManager, **kwargs) -> bool:
    return get_oracle().action_clear_queue()

@skill_handler("ai_snap")
def ai_snap_skill(vm: ViewportManager, **kwargs) -> bool:
    rect = vm.dock_rect
    if not rect: return False
    return get_oracle().action_add_to_queue(rect)

@skill_handler("ai_analyze")
def ai_analyze_skill(vm: ViewportManager, prompt: str = None, **kwargs) -> bool:
    oracle = get_oracle()
    # [V7.40] 投喂前必须先对焦浏览器，否则 Ctrl+V 会错发给 Tina 窗口
    oracle.action_focus_gpt_window()
    time.sleep(1.0)
    return oracle.action_send_queue_to_gpt(custom_prompt=prompt)

@skill_handler("scroll_up")
def scroll_up_skill(vm: ViewportManager, times: int = 5, **kwargs) -> bool:
    import win32api, win32con
    rect = vm.dock_rect
    if rect:
        # 丝滑对焦到窗口中心，确保滚轮生效
        smooth_move(int(rect["x"] + rect["width"]/2), int(rect["y"] + rect["height"]/2), duration=0.3)
    for _ in range(times):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 400, 0)
        time.sleep(0.1)
    return True

@skill_handler("scroll_down")
def scroll_down_skill(vm: ViewportManager, times: int = 5, **kwargs) -> bool:
    import win32api, win32con
    rect = vm.dock_rect
    if rect:
        # 丝滑对焦到窗口中心，确保滚轮生效
        smooth_move(int(rect["x"] + rect["width"]/2), int(rect["y"] + rect["height"]/2), duration=0.3)
    for _ in range(times):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -400, 0)
        time.sleep(0.1)
    return True


@skill_handler("find_and_click")
def find_and_click(vm: ViewportManager, keywords: list, **kwargs) -> bool:
    # 简易实现用于提交按钮
    agent = get_agent()
    rect = vm.dock_rect
    view_path = agent.vc.capture_screen(region={"top": int(rect["y"]), "left": int(rect["x"]), "width": int(rect["width"]), "height": int(rect["height"])})
    img = cv2.imread(view_path)
    ocr = agent.vc.get_ocr()
    results = ocr.read_screen(img)
    for (bbox, text, prob) in results:
        text_clean = text.lower().strip()
        if any(kw.lower() in text_clean for kw in keywords):
            tx, ty = (int((bbox[0][0] + bbox[1][0]) / 2), int((bbox[0][1] + bbox[2][1]) / 2))
            smooth_move(int(rect["x"] + tx), int(rect["y"] + ty), duration=0.5)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return True
    return False
