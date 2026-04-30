import re
import time
import cv2
import logging
import random
import win32api
import win32con
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager
from src.skills.humanize import smooth_move

logger = logging.getLogger("TextSkills")

def _log(msg):
    import time
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [TEXT_SKILL] {msg}")
    logger.info(msg)

@skill_handler("click_row_target")
def click_row_target(vm: ViewportManager, keywords: list, target_keyword: str, step_id: int = 0, **kwargs):
    """
    [V22.0 终极数学隔离版] 核心算法
    """
    import win32api, time as _time
    
    # [V31.2] N/A 决策：豆包判定该维度不适用，直接跳过不点击
    if target_keyword.strip().upper() == "N/A":
        _log(f"目标为 N/A，跳过该维度填表。")
        return True

    # [V31.4] 优先从 calibration_db.json 读取精准 dock_rect
    # vm.dock_rect 由 window-lock 步骤设置，但可能扫到错误的窗口尺寸
    import json as _json
    _calib_path = r"D:\Dev\autoplay\config\calibration_db.json"
    rect = None
    try:
        with open(_calib_path, "r", encoding="utf-8") as _f:
            rect = _json.load(_f).get("dock_rect")
    except Exception as _e:
        _log(f"读取 calibration_db 失败: {_e}，回退到 vm.dock_rect")
    if not rect:
        rect = vm.dock_rect
    if not rect:
        _log("致命错误：无法获取 dock_rect！")
        return False

    _log(f"截取 Tina dock 区域: x={rect['x']}, y={rect['y']}, w={rect['width']}, h={rect['height']}")

    from src.vision.capture import VisionCapture
    vc = VisionCapture()

    # [V31.5] 捕获时向右扩展 300px，确保 Both Good/Both Bad 不被右边缘截断
    # 点击坐标计算仍用原始 rect 的 origin (x, y)，扩展不影响绝对坐标
    rect_capture = dict(rect)
    rect_capture["width"] = rect["width"] + 300

    canvas = vc.capture_dock_region(rect_capture)
    if canvas is None:
        _log("致命错误：dock 区域截图失败！")
        return False

    ocr = vc.get_ocr()
    results = ocr.get_detailed_results(canvas)

    # [DEBUG] 保存截图到 temp，并在图上画出所有识别到的框，供目视检查
    try:
        import os
        import cv2
        import numpy as np
        debug_path = r"D:\Dev\autoplay\temp\debug_ocr_capture.jpg"
        os.makedirs(r"D:\Dev\autoplay\temp", exist_ok=True)
        debug_img = canvas.copy()
        for bbox, text, prob in results:
            pts = np.array(bbox, np.int32)
            cv2.polylines(debug_img, [pts], True, (0, 255, 0), 2)
            cv2.putText(debug_img, text, (int(pts[0][0]), int(pts[0][1]-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.imwrite(debug_path, debug_img)
        _log(f"[DEBUG] OCR 截图 (带框) 已保存: {debug_path}")
    except Exception as _de:
        _log(f"[DEBUG] 保存带框图片失败: {_de}")

    def clean_text(t):
        return re.sub(r'[^a-zA-Z0-9]', '', str(t)).lower()

    # 1. 建立数学围栏 (V22.0 核心：全域标题对位)
    ALL_DIMS = ["overall", "instruction", "idpreservation", "content", "visual", "generated", "absence"]
    _log("--- [V22.0] 建立全域数学坐标系 ---")
    all_anchors = []
    for bbox, text, prob in results:
        text_clean = clean_text(text)
        is_dim = any(dim_kw in text_clean for dim_kw in ALL_DIMS)
        # [V30.3] 特殊兜底：OCR 可能把 "ID Preservation" 拆成单独的 "ID"，需要专项识别
        if not is_dim and text_clean in ("id", "idpres"):
            is_dim = True
        if is_dim and len(text_clean) < 35:
            all_anchors.append({"text": text, "y": (bbox[0][1] + bbox[2][1]) / 2})
            _log(f"  锚点检测: '{text}' @ y={(bbox[0][1] + bbox[2][1]) / 2:.0f}")
    
    all_anchors = sorted(all_anchors, key=lambda x: x["y"])
    
    # 2. 定位“单间”车道
    y_min, y_max = 0, canvas.shape[0]
    target_y = None
    target_clean_list = [clean_text(kw) for kw in keywords]
    for i, a in enumerate(all_anchors):
        if any(tk in clean_text(a["text"]) for tk in target_clean_list):
            target_y = a["y"]
            if i > 0: y_min = (all_anchors[i-1]["y"] + a["y"]) / 2
            if i + 1 < len(all_anchors): y_max = (a["y"] + all_anchors[i+1]["y"]) / 2
            break

    if target_y is None:
        _log(f"目标行未找到！all_anchors 总数: {len(all_anchors)}, 关键词: {keywords}")
        return False

    _log(f"目标行定位成功: y={target_y:.0f}, 车道范围 y=[{y_min:.0f}, {y_max:.0f}]")

    # 3. 寻找车道内候选按钮并进行横向排序 (V23.0 序数对位法)
    candidates = []
    x_filter_threshold = canvas.shape[1] * 0.3  # Tina 窗口宽度的 30%（约 540px），左侧为标题区
    for bbox, text, prob in results:
        curr_x = (bbox[0][0] + bbox[1][0]) / 2
        curr_y = (bbox[0][1] + bbox[2][1]) / 2
        text_clean = clean_text(text)
        
        # 过滤：必须在 Y 轴车道内
        if not (y_min <= curr_y <= y_max): continue
        
        # [V31.0] X 轴过滤：坐标现在是相对于 Tina 窗口的，用 30% 窗口宽度作为左侧标题区隔离边界
        if curr_x < x_filter_threshold: continue
        
        # 识别按钮特征：包含 response 或 both
        if "response" in text_clean or "both" in text_clean or "good" in text_clean or "bad" in text_clean:
            candidates.append({"x": curr_x, "y": curr_y, "text": text_clean})
            _log(f"  ✓ 候选按钮: '{text}' @ ({curr_x:.0f}, {curr_y:.0f})")

    # 按 X 坐标从左到右排序
    candidates = sorted(candidates, key=lambda c: c["x"])
    _log(f"车道内检测到 {len(candidates)} 个候选按钮。")

    # 5. 计算目标点击坐标
    # [V32.0 终极方案: 混合定位]
    # 行的 Y 坐标：依然使用 OCR 检测到的标题 Y，加上微调偏移（如果有识别到按钮就用按钮的Y）
    # 列的 X 坐标：因为网页是响应式的且窗口大小已锁定在 width=1491，所以 A/B/Good/Bad 的列坐标是绝对固定的！
    # 直接硬编码 X 列坐标，彻底解决按钮被选中后底色改变导致 OCR 无法识别的问题。
    
    COLUMN_X = {
        "responsea": 1249,
        "responseb": 1341,
        "bothgood": 1433,
        "bothbad": 1507
    }
    
    target_pattern = clean_text(target_keyword)
    target_x_relative = COLUMN_X.get(target_pattern)
    if not target_x_relative:
        _log(f"未知目标选项: {target_keyword} (解析为 {target_pattern})，无法定位 X 坐标。")
        return False
        
    # 计算 Y 坐标
    # 如果该行有任何按钮被识别到，直接取它们的平均 Y 作为这行的完美 Y
    if candidates:
        button_y = sum(c["y"] for c in candidates) / len(candidates)
    else:
        # 如果一个按钮都没识别到，利用标题 Y 加上固定偏移 (通常按钮比标题低 10~16 像素)
        button_y = target_y + 12

    tx = int(rect["x"] + target_x_relative)
    ty = int(rect["y"] + button_y)

    _log(f"混合定位成功: {target_keyword} -> 行Y={button_y:.1f}, 列X={target_x_relative} => 绝对坐标({tx}, {ty})")

    # 执行点击
    import win32api
    import win32con
    import time
    win32api.SetCursorPos((tx, ty))
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    
    return True

class TextSkillsMixin:
    pass
