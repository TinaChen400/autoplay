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

    def capture_standard_view(self):
        """线程安全的单次抓拍"""
        config = self._load_config()
        dock_rect = None
        if config:
            raw = config.get("dock_rect")
            dock_rect = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        # 每次调用都创建独立的 mss 实例，彻底规避线程属性错误
        with mss.mss() as sct:
            screenshot = sct.grab(dock_rect) if dock_rect else sct.grab(sct.monitors[1])
            save_path = os.path.join(self.records_dir, "skill_msi_last_view.jpg")
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
            return save_path

    def find_thumbnail_rect(self, anchor_x, anchor_y, img):
        h, w, _ = img.shape
        roi_top, roi_bottom = anchor_y, min(anchor_y + 300, h)
        roi_left, roi_right = max(anchor_x - 100, 0), min(anchor_x + 300, w)
        
        roi_img = img[roi_top:roi_bottom, roi_left:roi_right]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if 50 < rw < 200 and 50 < rh < 200:
                return rx + roi_left + rw // 2, ry + roi_top + rh // 2
        return None, None

    def click_input_thumbnail(self):
        print("\n--- 执行技能: click_input_thumbnail ---")
        view_path = self.capture_standard_view()
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)
        anchor_x, anchor_y = -1, -1
        keywords = ["inputs", "input", "source", "output"]
        
        for line in context.split('\n'):
            if any(k in line.lower() for k in keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    anchor_x, anchor_y = int(parts[0]), int(parts[1])
                    break
                except: continue
        
        if anchor_y == -1: return False
        target_x, target_y = self.find_thumbnail_rect(anchor_x, anchor_y, img)
        config = self._load_config()
        if not config: return False
        
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        tx, ty = (base_x + target_x, base_y + target_y) if target_x else (base_x + anchor_x, base_y + anchor_y + 120)
        self.agent.click_at(tx, ty)
        return True

    def wait_for_visual_change(self, timeout=10, threshold=15.0):
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

    def interact_with_large_image(self):
        if not self.wait_for_visual_change(): return False
        config = self._load_config()
        if not config: return False
        data = config['dock_rect']
        cx, cy = data['x'] + data['width'] // 2, data['y'] + data['height'] // 2
        self.agent.double_click_at(cx, cy) 
        time.sleep(1.0)
        self.agent.press_key_sequence(['down', 'right', 'left', 'up'], interval=0.5, hold_time=0.15)
        return True

if __name__ == "__main__":
    skills = MSISkills()
    if not skills.click_input_thumbnail(): skills.interact_with_large_image()
