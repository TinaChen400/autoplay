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
from src.utils.viewport_manager import ViewportManager

logger = logging.getLogger("AtomicSkills")

def get_agent():
    # 模拟获取 agent 实例
    class MockAgent:
        def __init__(self):
            self.records_dir = r"D:\Dev\autoplay\records"
            from src.utils.ocr_reader import OCRReader
            from src.utils.vision import VisionCapture
            self.vc = VisionCapture()
    return MockAgent()

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
    from src.utils.window_lock import WindowLock
    locker = WindowLock("Tina")
    success = locker.lock_and_align(x, y, width, height)
    if success: vm.update_dock_rect({"x": x, "y": y, "width": width, "height": height})
    return success

@skill_handler("ai_clear")
def ai_clear_skill(vm: ViewportManager, **kwargs) -> bool:
    from src.execution.gpt_oracle import GPTOracle
    return GPTOracle().action_clear_queue()

@skill_handler("ai_snap")
def ai_snap_skill(vm: ViewportManager, **kwargs) -> bool:
    from src.execution.gpt_oracle import GPTOracle
    rect = vm.dock_rect
    if not rect: return False
    return GPTOracle().action_add_to_queue(rect)

@skill_handler("ai_analyze")
def ai_analyze_skill(vm: ViewportManager, prompt: str = None, **kwargs) -> bool:
    from src.execution.gpt_oracle import GPTOracle
    return GPTOracle().action_send_queue_to_gpt(custom_prompt=prompt)

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
    模拟人类漫无目的地微微滑过界面（模拟阅读/等待）。
    每次生成的轨迹都是唯一的。
    """
    import random
    import math
    
    rect = vm.dock_rect
    if not rect: return False
    
    # 获取当前鼠标位置
    curr_x, curr_y = win32api.GetCursorPos()
    
    # 确定移动范围（在窗口内随机找几个点）
    target_x = rect["x"] + random.randint(200, rect["width"] - 200)
    target_y = rect["y"] + random.randint(200, rect["height"] - 200)
    
    logger.info(f"Simulating human move from ({curr_x},{curr_y}) to ({target_x},{target_y})")
    
    # 模拟非线性轨迹（简单的插值+随机抖动）
    for i in range(steps):
        # 计算插值比例
        t = (i + 1) / steps
        # 加入正弦波动模拟手抖
        jitter = math.sin(t * math.pi) * 10
        
        step_x = int(curr_x + (target_x - curr_x) * t + random.randint(-5, 5))
        step_y = int(curr_y + (target_y - curr_y) * t + jitter)
        
        win32api.SetCursorPos((step_x, step_y))
        
        # 1. 基础节奏（慢-快-慢）
        base_sleep = (duration / steps) * (1.5 - math.sin(t * math.pi))
        
        # 2. 引入“混沌系数”：每一步都有随机的速度波动 (0.5倍 到 2.0倍 波动)
        chaos_factor = random.uniform(0.5, 2.0)
        final_sleep = base_sleep * chaos_factor
        
        # 3. 随机“发呆”：模拟人在某个细节处停顿
        if random.random() < 0.1: # 10% 概率停顿
            time.sleep(random.uniform(0.1, 0.4))
            
        time.sleep(max(0.005, final_sleep))
        
    return True

@skill_handler("auto_page_capture")
def auto_page_capture(vm: ViewportManager, max_pages: int = 10, **kwargs) -> bool:
    """
    全页面自动抓取：从顶翻到底，智能判断触底，每页存入 AI 队列。
    """
    from src.execution.gpt_oracle import GPTOracle
    oracle = GPTOracle()
    
    # 1. 先滚回最顶部（多滚几次确保到位）
    scroll_up_skill(vm, times=8)
    time.sleep(1.0)
    
    last_text_fingerprint = ""
    pages_captured = 0
    
    for i in range(max_pages):
        # A. 抓取并存入队列
        ai_snap_skill(vm)
        pages_captured += 1
        logger.info(f"Captured page {pages_captured}")
        
        # B. 获取当前视野的“文字指纹”用于触底检测
        agent = get_agent()
        rect = vm.dock_rect
        view_path = agent.vc.capture_screen(region={"top": int(rect["y"]), "left": int(rect["x"]), "width": int(rect["width"]), "height": int(rect["height"])})
        img = cv2.imread(view_path)
        ocr = agent.vc.get_ocr()
        results = ocr.read_screen(img)
        # 取所有文字的前200个字符作为指纹
        current_text = "".join([r[1] for r in results])[:200]
        
        if current_text == last_text_fingerprint and i > 0:
            logger.info("Bottom reached (content identical to last page). Stopping.")
            break
            
        last_text_fingerprint = current_text
        
        # C. 向下大幅度滚动（约一个屏幕高度）
        scroll_down_skill(vm, times=8)
        time.sleep(1.2) # 等待加载/渲染
        
    logger.info(f"Total pages captured: {pages_captured}")
    return True

@skill_handler("press_keys")
def press_keys_skill(vm: ViewportManager, keys: list, interval: float = 0.5, **kwargs) -> bool:
    """模拟按下方向键或功能键"""
    import pyautogui
    key_map = {"up": "up", "down": "down", "left": "left", "right": "right", "esc": "esc", "enter": "enter"}
    for k in keys:
        py_key = key_map.get(k.lower(), k.lower())
        pyautogui.press(py_key)
        time.sleep(interval)
    return True

@skill_handler("click_landmark")
def click_landmark_skill(vm: ViewportManager, keywords: list, optional: bool = False, offset_x: int = 0, offset_y: int = 0, **kwargs) -> bool:
    """根据关键词模糊搜索并在全屏范围内寻找并点击，支持偏移量和红点调试"""
    agent = get_agent()
    rect = vm.dock_rect
    img_path = agent.vc.capture_screen(region={"top": int(rect["y"]), "left": int(rect["x"]), "width": int(rect["width"]), "height": int(rect["height"])})
    img = cv2.imread(img_path)
    ocr = agent.vc.get_ocr()
    results = ocr.read_screen(img)
    
    found = False
    for kw in keywords:
        for res in results:
            text_detected = res[1].lower()
            if kw.lower() in text_detected:
                # 转换为全局坐标
                box = res[0]
                center_x = (box[0][0] + box[2][0]) / 2
                center_y = (box[0][1] + box[2][1]) / 2
                
                final_x = center_x + offset_x
                final_y = center_y + offset_y
                
                # --- 红点调试逻辑 ---
                debug_img = img.copy()
                cv2.circle(debug_img, (int(final_x), int(final_y)), 15, (0, 0, 255), -1)
                debug_path = os.path.join(agent.records_dir, "click_debug.jpg")
                cv2.imwrite(debug_path, debug_img)
                logger.info(f"DEBUG: Click evidence saved to {debug_path}")
                # ------------------

                abs_x = rect["x"] + final_x
                abs_y = rect["y"] + final_y
                
                win32api.SetCursorPos((int(abs_x), int(abs_y)))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                logger.info(f"Clicked landmark: {res[1]} (matched '{kw}') with offset ({offset_x}, {offset_y})")
                return True
    
    if not optional:
        logger.warning(f"Landmark NOT found: {keywords}")
    return optional
    
    if not optional:
        logger.warning(f"Landmark NOT found: {keywords}")
    return optional

@skill_handler("sleep")
def sleep_skill(vm: ViewportManager, seconds: float = 1.0, **kwargs) -> bool:
    """精准等待"""
    # 支持 "2.0-5.0" 这种随机范围
    if isinstance(seconds, str) and "-" in seconds:
        import random
        low, high = map(float, seconds.split("-"))
        actual = random.uniform(low, high)
    else:
        actual = float(seconds)
    time.sleep(actual)
    return True

@skill_handler("click_landmark_radar")
def click_landmark_radar_skill(vm: ViewportManager, keywords: list, firezone_x: int = 720, **kwargs) -> bool:
    """视觉雷达对焦：在中线以内寻找放大镜图标并点击"""
    agent = get_agent()
    rect = vm.dock_rect
    img_path = agent.vc.capture_screen(region={"top": int(rect["y"]), "left": int(rect["x"]), "width": int(rect["width"]), "height": int(rect["height"])})
    img = cv2.imread(img_path)
    
    # 1. 收集所有可能的锚点高度
    ocr = agent.vc.get_ocr()
    results = ocr.read_screen(img)
    
    anchors = []
    for res in results:
        text_detected = res[1].lower()
        if any(kw.lower() in text_detected for kw in keywords):
            # 这里的 x 坐标要符合火区逻辑（如果是找 B 栏，锚点通常在 720 以后）
            cx = (res[0][0][0] + res[0][1][0]) / 2
            cy = (res[0][0][1] + res[0][2][1]) / 2
            
            # 如果是找 A 栏 (firezone=720)，锚点应该在 720 以内
            # 如果是找 B 栏 (firezone=1440)，锚点应该在 720 以后
            if firezone_x <= 720 and cx < 720:
                anchors.append(cy)
            elif firezone_x > 720 and cx >= 720:
                anchors.append(cy)
            
    if not anchors:
        logger.warning(f"Radar failed: No valid anchors found for {keywords} in zone {firezone_x}")
        return False

    # 2. 对每个锚点高度进行视觉雷达扫描
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    debug_img = img.copy()
    cv2.line(debug_img, (firezone_x, 0), (firezone_x, rect["height"]), (0, 255, 255), 2)
    
    best_target = None
    min_dist = 9999
    
    # 找所有圆圈
    all_circles = []
    for cnt in contours:
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        all_circles.append(((int(x), int(y)), radius))
        cv2.circle(debug_img, (int(x), int(y)), int(radius), (200, 200, 200), 1)

    # 尝试匹配每一个锚点
    for anchor_y in anchors:
        cv2.line(debug_img, (0, int(anchor_y)), (firezone_x, int(anchor_y)), (255, 0, 255), 1)
        for center, radius in all_circles:
            x, y = center
            # 过滤逻辑：在中线范围内，高度匹配锚点
            zone_min = 720 if firezone_x > 720 else 0
            is_candidate = zone_min <= x < firezone_x and abs(y - anchor_y) < 60 and 5 < radius < 35
            if is_candidate:
                cv2.circle(debug_img, center, int(radius), (0, 255, 0), 2)
                dist_to_mid = firezone_x - x
                if dist_to_mid < min_dist:
                    min_dist = dist_to_mid
                    best_target = center

    # 存调试图
    debug_path = os.path.join(agent.records_dir, "radar_debug.jpg")
    if best_target:
        cv2.circle(debug_img, best_target, 15, (255, 0, 0), 3)
    cv2.imwrite(debug_path, debug_img)

    if best_target:
        abs_x = rect["x"] + best_target[0]
        abs_y = rect["y"] + best_target[1]
        win32api.SetCursorPos((int(abs_x), int(abs_y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        logger.info(f"RADAR LOCKED: ICON DETECTED AT {best_target}. FIRE!")
        return True

    logger.warning(f"Radar scan completed: No targets found near any of the {len(anchors)} anchors.")
    return False

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
