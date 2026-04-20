import sys
import json
import os
import cv2
import time
import numpy as np
import mss

sys.path.append(r"D:/Dev/autoplay")
from src.utils.vision import VisionCapture
from src.utils.ocr_reader import OCRReader
from src.execution.remote_agent import RemoteAgent

class MSISkills:
    """
    MSI 原子技能积木库 (V14 Lego Edition)
    """
    def __init__(self):
        self.agent = RemoteAgent(profile_name="MSI")
        self.vc = VisionCapture()
        self.ocr = OCRReader()
        self.records_dir = r"D:/Dev/autoplay/records"
        self.db_path = r"D:/Dev/autoplay/config/calibration_db.json"

    def _load_config(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    return json.load(f)
            except: pass
        return None

    def action_screenshot(self, label="view"):
        """原子积木：拍摄物理对位快照"""
        config = self._load_config()
        dock_rect = None
        if config:
            raw = config.get("dock_rect")
            dock_rect = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        with mss.mss() as sct:
            screenshot = sct.grab(dock_rect) if dock_rect else sct.grab(sct.monitors[1])
            save_path = os.path.join(self.records_dir, f"snap_{label}.jpg")
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
            print(f"[SKILL] 快照保存: {save_path}")
            return save_path

    def action_click_landmark(self, keywords=["input"]):
        """原子积木：地标识别点击 (V7 寻锚)"""
        print(f"\n[SKILL] 寻找地标点击: {keywords}")
        view_path = self.action_screenshot("landmark_search")
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)
        
        ax, ay = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    ax, ay = int(parts[0]), int(parts[1])
                    break
                except: continue
        
        if ay == -1: return False

        # 视觉边缘微调
        tx, ty = self._find_thumbnail_center(ax, ay, img)
        config = self._load_config()
        if not (config and tx):
            # 降级：仅使用文本偏移
            tx, ty = config['dock_rect']['x'] + ax, config['dock_rect']['y'] + ay + 120
        else:
            tx, ty = config['dock_rect']['x'] + tx, config['dock_rect']['y'] + ty

        self.agent.click_at(tx, ty)
        return True

    def _find_thumbnail_center(self, ax, ay, img):
        h, w, _ = img.shape
        roi = img[ay:min(ay+300, h), max(ax-100, 0):min(ax+300, w)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(cv2.GaussianBlur(gray, (3,3), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if 50 < rw < 200 and 50 < rh < 200:
                return rx + max(ax-100, 0) + rw // 2, ry + ay + rh // 2
        return None, None

    def action_wait_visual(self, threshold=15.0, timeout=10):
        """原子积木：视觉变化等待"""
        config = self._load_config()
        if not config: return False
        raw = config["dock_rect"]
        monitor = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        with mss.mss() as sct:
            base_frame = np.array(sct.grab(monitor))
            base_img = cv2.cvtColor(base_frame, cv2.COLOR_BGRA2GRAY)
            start_time = time.time()
            while time.time() - start_time < timeout:
                curr_img = cv2.cvtColor(np.array(sct.grab(monitor)), cv2.COLOR_BGRA2GRAY)
                diff = cv2.absdiff(base_img, curr_img)
                _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                roi_h, roi_w = int(base_img.shape[0] * 0.8), int(base_img.shape[1] * 0.8)
                y1, x1 = (base_img.shape[0] - roi_h)//2, (base_img.shape[1] - roi_w)//2
                roi_diff = diff_thresh[y1:y1+roi_h, x1:x1+roi_w]
                if (cv2.countNonZero(roi_diff) / (roi_h * roi_w)) * 100 > threshold: return True
                time.sleep(0.5)
        return False

    def action_press_keys(self, keys=["down"]):
        """原子积木：按键序列注入"""
        print(f"[SKILL] 注入按键: {keys}")
        config = self._load_config()
        if config:
            data = config['dock_rect']
            cx, cy = data['x'] + data['width'] // 2, data['y'] + data['height'] // 2
            self.agent.double_click_at(cx, cy)
            time.sleep(0.5)
        self.agent.press_key_sequence(keys, interval=0.5, hold_time=0.15)
        return True

    def action_zoom_pan_reset(self, landmark_keywords=["ref"], scroll_amount=3,
                               pan_dx=80, pan_dy=40, reset_by_double_click=True):
        """
        原子积木：在 Ref 区域执行 Zoom In -> PAN -> 双击还原 的完整交互序列。
        1. 视觉寻锚 Ref1/Ref 地标并点击
        2. 鼠标滚轮 Zoom In
        3. 按住左键拖拽 PAN
        4. 双击还原原始视图
        """
        import pydirectinput
        import win32api
        import win32con

        print(f"\n[SKILL] 执行 Zoom/Pan/Reset 序列: 地标={landmark_keywords}")

        # --- Step 1: 找到 Ref 图片位置 ---
        view_path = self.action_screenshot("ref_search")
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)

        ax, ay = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in landmark_keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    ax, ay = int(parts[0]), int(parts[1])
                    print(f"[SKILL] Ref 地标定位: ({ax}, {ay})")
                    break
                except: continue

        if ay == -1:
            print("[SKILL] 未找到 Ref 地标，操作终止。")
            return False

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # 转换为物理绝对坐标
        target_x = base_x + ax
        target_y = base_y + ay + 60  # 偏移到图片区域（标题下方）

        # --- Step 2: 单击聚焦到 Ref 图 ---
        print(f"[SKILL] 点击 Ref 图位置: ({target_x}, {target_y})")
        self.agent.click_at(target_x, target_y)
        time.sleep(0.5)

        # --- Step 3: 鼠标滚轮 Zoom In ---
        print(f"[SKILL] 滚轮 Zoom In x{scroll_amount}")
        pydirectinput.moveTo(target_x, target_y)
        for _ in range(scroll_amount):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
            time.sleep(0.15)
        time.sleep(0.5)

        # --- Step 4: 按住左键拖拽 PAN ---
        print(f"[SKILL] PAN 拖拽: dx={pan_dx}, dy={pan_dy}")
        pydirectinput.mouseDown(button='left')
        time.sleep(0.1)
        # 分步拖拽，模拟真实手势
        steps = 10
        for i in range(steps):
            pydirectinput.moveRel(pan_dx // steps, pan_dy // steps)
            time.sleep(0.03)
        pydirectinput.mouseUp(button='left')
        time.sleep(0.5)

        # --- Step 5: 双击还原视图 ---
        if reset_by_double_click:
            print("[SKILL] 双击还原原始视图")
            pydirectinput.doubleClick(target_x, target_y)
            time.sleep(0.3)

        print("[SKILL] Zoom/Pan/Reset 完成。")
        return True
