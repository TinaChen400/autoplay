# -*- coding: utf-8 -*-
import time
import win32api
import win32con
import os
import cv2
import numpy as np
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import smooth_move

@skill_handler("action_click_smart")
def action_click_smart(vm: ViewportManager, keywords: list = None, landmark_image: str = None, anchor_text: str = "Response", offset_x: int = 0, offset_y: int = 0, **kwargs):
    """
    [V19.3] 智能地标点击：增加 ROI 区域限制，排除侧边栏干扰。
    """
    import logging
    logger = logging.getLogger("VisualAnchorSkills")
    
    # 1. 获取物理对位边界
    import json
    calib_path = r"D:\Dev\autoplay\config\calibration_db.json"
    rect = None
    try:
        if os.path.exists(calib_path):
            with open(calib_path, "r", encoding="utf-8") as f:
                rect = json.load(f).get("dock_rect")
    except: pass
    
    if not rect:
        rect = vm.dock_rect
    
    if not rect:
        print("[SKILL] action_click_smart: No dock_rect available.")
        return False

    # 2. 视觉采集 (全量采集用于锚点定位)
    from src.vision.capture import VisionCapture
    vc = VisionCapture()
    canvas = vc.capture_dock_region(rect)
    if canvas is None: return False

    # 3. 确定搜索区域 (ROI)
    from src.vision.recognition_expert import RecognitionExpert
    expert = RecognitionExpert(vision_capture=vc)
    
    # [V32.9] 动态 X 轴 ROI 逻辑：
    # 如果指定了 A/B，则根据 A/B 自动锁定左右半边
    roi_x_start = 0
    roi_w = canvas.shape[1]
    
    if anchor_text:
        low_anchor = anchor_text.lower()
        if "a" in low_anchor:
            roi_x_start = 100 # 左侧图像区
            roi_w = 600
        elif "b" in low_anchor:
            roi_x_start = 600 # 右侧图像区
            roi_w = 500
            
    roi_y_start = 0
    roi_h = canvas.shape[0]
    
    # 如果指定了行锚点文字 (例如 "Response A")，则进行垂直精确锁定
    if anchor_text:
        print(f"[SKILL] Searching for row anchor: '{anchor_text}'...")
        # [V22.3] 模糊语义增强：识别 Respon 开头的任何文字 (兼容 Responge8 等 OCR 错误)
        ocr_results = vc.get_ocr().get_detailed_results(canvas)
        
        all_candidates = []
        best_anchor_y = None
        for (bbox, text, prob) in ocr_results:
            clean_text = text.lower().replace(" ", "")
            if "respon" in clean_text:
                center_x = int(np.mean([p[0] for p in bbox]))
                center_y = int(np.mean([p[1] for p in bbox]))
                
                # 空间判定：A 通常在左半边 (X < 600)，B 在右半边 (X > 600)
                # [V32.1] 智能分流补丁：只有关键词以 "Response" 开头时才强制区分 A/B
                is_target = False
                if anchor_text.lower().startswith("response"):
                    if "a" in anchor_text.lower():
                        if center_x < 600: is_target = True
                    elif "b" in anchor_text.lower():
                        if center_x >= 600: is_target = True
                else:
                    # 对于 generic 锚点（如 the better response），默认全匹配
                    is_target = True
                
                if is_target:
                    # [V32.2] 顶部优先补丁：搜集所有可能的锚点，最后取最靠上的那个
                    all_candidates.append({"y": center_y, "x": center_x, "text": text})
                    
        if all_candidates:
            # 按 Y 轴升序排序（最顶部的排第一）
            all_candidates = sorted(all_candidates, key=lambda x: x["y"])
            best_anchor = all_candidates[0]
            best_anchor_y = best_anchor["y"]
            print(f"[SKILL] Top-most anchor selected: '{best_anchor['text']}' at ({best_anchor['x']}, {best_anchor['y']})")
            
            # [V32.3] 精准 Y 轴偏移：因为 Response A 标题离图片很近，恢复为 40-100px 偏移
            roi_y_start = best_anchor_y + 40
            roi_h = 150 # 稍微收窄视野，减少干扰
            print(f"[SKILL] Top-Down ROI Y: [{roi_y_start}, {roi_y_start + roi_h}]")
        else:
            print(f"[SKILL] Could not find any anchor resembling '{anchor_text}'.")
            return False
            
    # [V22.4] 执行最终裁切 (X: 800-900, Y: 基于锚点动态锁定)
    roi_canvas = canvas[roi_y_start : min(canvas.shape[0], roi_y_start + roi_h), roi_x_start : min(canvas.shape[1], roi_x_start + roi_w)]
    
    # 4. 在 ROI 区域内进行模板匹配 (可选，如果匹配不到则点中心)
    target_pos_roi = expert.find_landmark(roi_canvas, landmark_image=landmark_image)
    
    # 最终点击坐标计算
    if target_pos_roi:
        # 找到了图标，用图标坐标
        rx = target_pos_roi[0] + roi_x_start
        ry = target_pos_roi[1] + roi_y_start
        print(f"[SKILL] Icon matched at ROI relative: {target_pos_roi}")
    else:
        # 没找到图标，但文字锚点是对的，直接点 ROI 区域中心 (保底逻辑)
        rx = roi_x_start + (roi_w // 2)
        ry = roi_y_start + (roi_h // 2)
        print(f"[SKILL] Icon match failed, but anchor is solid. Clicking ROI center: ({rx}, {ry})")
    
    # 坐标映射还原
    tx = int(rect["x"] + rx + offset_x)
    ty = int(rect["y"] + ry + offset_y)
    
    # [DEBUG] 保存可视化诊断图
    try:
        debug_img = canvas.copy()
        cv2.rectangle(debug_img, (roi_x_start, roi_y_start), (roi_x_start + roi_w, roi_y_start + roi_h), (0, 255, 255), 2)
        cv2.circle(debug_img, (int(rx), int(ry)), 8, (0, 0, 255), -1)
        cv2.imwrite(r"D:\Dev\autoplay\temp\debug_visual_anchor.jpg", debug_img)
    except: pass
    
    # 6. 执行物理交互 (梅花阵地毯式点击)
    print(f"[SKILL] Executing Spray Click around: ({tx}, {ty})")
    
    # 核心对准
    win32api.SetCursorPos((tx, ty))
    time.sleep(0.2)
    
    # 定义 5 个微偏点，确保覆盖整个图标区域
    offsets = [
        (0, 0),   # 中心
        (-6, -6), # 左上
        (6, -6),  # 右上
        (-6, 6),  # 左下
        (6, 6)    # 右下
    ]
    
    for ox, oy in offsets:
        curr_x, curr_y = tx + ox, ty + oy
        win32api.SetCursorPos((curr_x, curr_y))
        time.sleep(0.05)
        # 执行一次深按
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.05)
        
    return True
