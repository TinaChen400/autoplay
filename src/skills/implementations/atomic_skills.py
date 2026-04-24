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

    # 执行物理点击
    win32api.SetCursorPos((int(rect["x"] + target_pos[0]), int(rect["y"] + target_pos[1])))
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
        # 先把鼠标移到窗口中心，确保滚轮生效
        win32api.SetCursorPos((int(rect["x"] + rect["width"]/2), int(rect["y"] + rect["height"]/2)))
    for _ in range(times):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 400, 0)
        time.sleep(0.1)
    return True

@skill_handler("scroll_down")
def scroll_down_skill(vm: ViewportManager, times: int = 5, **kwargs) -> bool:
    import win32api, win32con
    rect = vm.dock_rect
    if rect:
        # 先把鼠标移到窗口中心，确保滚轮生效
        win32api.SetCursorPos((int(rect["x"] + rect["width"]/2), int(rect["y"] + rect["height"]/2)))
    for _ in range(times):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -400, 0)
        time.sleep(0.1)
    return True

@skill_handler("human_idle_move")
def human_idle_move(vm: ViewportManager, duration: float = 2.0, steps: int = 15, **kwargs) -> bool:
    """
    [V7.65] 拟人化安全漫游：三重物理锁死，绝不越界
    """
    import random
    import time
    import win32api
    import win32gui
    import win32con
    
    # 0. 基础环境感知
    screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    
    # [V7.80] 智能探测模式：放宽匹配 + 失败全量诊断
    from src.drivers.window import WindowManager
    import win32gui
    
    wm = WindowManager(keywords=["Tina", "流畅"])
    rect_raw = wm.get_window_rect()
    
    if not rect_raw:
        print("!!! [IDLE_MOVE] 警告：找不到 Tina 窗口，正在扫描全系统窗口标题以供诊断...")
        def dump_titles(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t: print(f"  - [DEBUG] 发现窗口: {t}")
        win32gui.EnumWindows(dump_titles, None)
        
        # 兜底：执行屏幕中心漫游，不中断任务
        rect = {"x": 500, "y": 300, "w": 800, "h": 600}
        target_hwnd = None
    else:
        print(f">>> [IDLE_MOVE] 锁定成功！[{rect_raw.get('title')}]")
        rect = {"x": rect_raw["left"], "y": rect_raw["top"], 
                "w": rect_raw["width"], "h": rect_raw["height"]}
        target_hwnd = wm.hwnd
        
    # [V7.71] 修正激活逻辑：直接调用 Win32 原生句柄
    if target_hwnd:
        try:
            # 如果窗口最小化了，先恢复它
            if win32gui.IsIconic(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.2)
        except Exception as e:
            print(f"!!! [IDLE_MOVE] 激活窗口失败: {e}")
    
    print(f">>> [IDLE_MOVE] 已锁定目标漫游区: {rect}")
    
    # 2. 漫游目标：窗口左侧 20% - 60% 区域 (避开右侧滚动条)
    target_x = rect["x"] + int(rect["w"] * 0.2) + random.randint(0, int(rect["w"] * 0.4))
    target_y = rect["y"] + int(rect["h"] * 0.3) + random.randint(0, int(rect["h"] * 0.4))
    
    # 3. 初始归位 (先回到安全区)
    win32api.SetCursorPos((target_x, target_y))
    time.sleep(0.1)
    
    curr_x, curr_y = win32api.GetCursorPos()
    
    # 4. 漫游轨迹 (双重物理锁死)
    for i in range(steps):
        t = (i + 1) / steps
        step_x = int(curr_x + (target_x - curr_x) * t)
        step_y = int(curr_y + (target_y - curr_y) * t)
        
        # 钳制在窗口内，留出 150 像素安全边距
        final_x = max(rect["x"] + 150, min(step_x, rect["x"] + rect["w"] - 150))
        final_y = max(rect["y"] + 150, min(step_y, rect["y"] + rect["h"] - 150))
        
        win32api.SetCursorPos((final_x, final_y))
        time.sleep(duration / steps)
        
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
            win32api.SetCursorPos((int(rect["x"] + tx), int(rect["y"] + ty)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return True
    return False
