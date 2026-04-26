import time
import random
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

def _log(msg):
    from src.skills.implementations.ai_skills import get_bridge
    bridge = get_bridge()
    if bridge:
        bridge._log(f"[TEXT_SKILL] {msg}")
    else:
        logger.info(msg)
    print(f">>> [OCR_DEBUG] {msg}")

@skill_handler("click_row_target")
def click_row_target(vm: ViewportManager, keywords: list, target_keyword: str, offset_x=0, offset_y=0, step_id=0, **kwargs):
    """
    [V15.9] 深度交互版：自动避让鼠标 + 模拟人类深按点击。
    """
    target_rel_pos = None # 强制第一行初始化，防止 UnboundLocalError
    rect = vm.dock_rect
    if not rect: return False
    
    win_px, win_py = rect['x'], rect['y']
    logi_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    phys_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    scale = phys_w / logi_w

    # --- [V17.3] 避让逻辑：移到 (10,10)，彻底消除悬浮干扰，且不再依赖 PyAutoGUI ---
    win32api.SetCursorPos((10, 10))
    time.sleep(0.5) # 强力防抖等待

    from src.vision.capture import VisionCapture
    vc = VisionCapture()
    ocr = vc.get_ocr()
    # --- [V17.0] 抓图稳定性增强 ---
    frame_np = vc.capture_dock_region({"x": win_px, "y": win_py, "width": rect['width'], "height": rect['height']})
    if frame_np is None: return False
    
    # 高清预处理 (V16.6 核心)
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
        return re.sub(r'[^a-zA-Z0-9]', '', str(t)).lower()

    # 1. 扫描视野内所有锚点并按 Y 坐标排序
    _log(f"--- [OCR DEBUG] 数学车道划定中... ---")
    all_anchors = []
    for i, (bbox, text, prob) in enumerate(results):
        text_clean = clean_text(text)
        for kw_raw in keywords:
            if clean_text(kw_raw) in text_clean and len(text_clean) < 35:
                p1 = (int(bbox[0][0]/2), int(bbox[0][1]/2))
                p2 = (int(bbox[2][0]/2), int(bbox[2][1]/2))
                all_anchors.append({"text": text, "y": (p1[1] + p2[1]) / 2})
                break
    
    # 按从上到下排序，建立物理层级
    all_anchors = sorted(all_anchors, key=lambda x: x["y"])
    
    # 2. 确定当前目标的“数学车道”上下限 (中线分割法)
    y_min, y_max = 0, canvas.shape[0]
    target_y = None
    for i, a in enumerate(all_anchors):
        if any(clean_text(kw) in clean_text(a["text"]) for kw in keywords):
            target_y = a["y"]
            if i > 0:
                y_min = (all_anchors[i-1]["y"] + a["y"]) / 2
            if i + 1 < len(all_anchors):
                y_max = (a["y"] + all_anchors[i+1]["y"]) / 2
            break

    if target_y is None:
        _log(f"失败：视野内未找到目标锚点 {keywords}")
        return False

    _log(f"锁定车道: [{target_keyword}] Y={target_y:.1f}, 范围: {y_min:.1f} - {y_max:.1f}")

    # 3. 在全域搜索，但只取掉进“车道”内的匹配按钮
    best_match = None
    min_dist = 999
    target_pattern = clean_text(target_keyword)
    
    for i, (bbox, text, prob) in enumerate(results):
        p1 = (int(bbox[0][0]/2), int(bbox[0][1]/2))
        p2 = (int(bbox[2][0]/2), int(bbox[2][1]/2))
        curr_y = (p1[1] + p2[1]) / 2
        text_clean = clean_text(text)
        
        # 物理分区：按钮必须在右侧 70% 区域 
        if p1[0] < (canvas.shape[1] * 0.3): continue

        # [V22.0] 数学隔离：检查是否在当前标题的专属高度区间内
        if not (y_min <= curr_y <= y_max):
            continue

        # 匹配逻辑：文字识别 OR 坐标领地强制映射
        is_match = False
        if target_pattern in text_clean:
            is_match = True
        elif "response" in target_pattern:
            is_in_zone = False
            if "responsea" in target_pattern and 1300 < p1[0] < 1375: is_in_zone = True
            if "responseb" in target_pattern and 1385 < p1[0] < 1470: is_in_zone = True
            if "bothgood" in target_pattern and 1480 < p1[0] < 1560: is_in_zone = True
            
            text_fuzzy = text_clean.replace('8', 'b').replace('4', 'a').replace('6', 'b')
            core = "a" if "a" in target_pattern else "b"
            if is_in_zone or core == text_fuzzy:
                is_match = True

        if is_match:
            # 在车道内，取离标题最近的
            dist = abs(curr_y - target_y)
            if dist < min_dist:
                min_dist = dist
                best_match = ((p1[0] + p2[0]) / 2, curr_y)
                cv2.rectangle(canvas, p1, p2, (0, 255, 0), 2)

    if best_match:
        target_rel_pos = best_match
        _log(f"锁定最近按钮: at {target_rel_pos} (垂直偏离: {min_dist}px)")

    if target_rel_pos:
        tx = int((win_px + target_rel_pos[0]) / scale) + offset_x
        ty = int((win_py + target_rel_pos[1]) / scale) + offset_y
        
        # 绘制准星并保存
        cv2.drawMarker(canvas, (int(target_rel_pos[0]), int(target_rel_pos[1])), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.imwrite(rf"D:\Dev\autoplay\temp\result_step_{step_id}.jpg", canvas)
        
        # --- [V16.0] 拟人化重塑：弧线移动 + 随机落点 + 点击迟疑 ---
        from src.skills.humanize import smooth_move, human_jitter, decision_hesitation
        
        # 1. 产生微小落点偏差 (±3px)
        tx += random.randint(-3, 3)
        ty += random.randint(-3, 3)
        
        # 2. 思考与移动
        decision_hesitation(0.3, 0.8) # 模拟人眼扫到目标后的反应时间
        smooth_move(tx, ty, duration=random.uniform(0.4, 0.7))
        
        # 3. 对准微调 (抖动)
        human_jitter(tx, ty, intensity=2)
        
        # 4. 执行深度按压
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(random.uniform(0.1, 0.25)) # 模拟手指按压的时长波动
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        logger.info(f"[HUMAN_HIT] Step {step_id} 已拟人化点击: ({tx}, {ty})")
        return True
    
    return False

class TextSkillsMixin:
    pass
