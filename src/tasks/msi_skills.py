import sys
import json
import os
import cv2
import time

sys.path.append(r"D:/Dev/autoplay")
from src.utils.vision import VisionCapture
from src.utils.ocr_reader import OCRReader
from src.execution.remote_agent import RemoteAgent

class MSISkills:
    """
    专门针对 MSI 远程环境的自动化技能包。
    所有动作均包含[自动录制快照]与[语义对位]逻辑。
    """
    def __init__(self):
        self.agent = RemoteAgent(profile_name="MSI")
        self.vc = VisionCapture()
        self.ocr = OCRReader()
        self.records_dir = r"D:/Dev/autoplay/records"

    def capture_standard_view(self):
        """记录并获取当前 MSI 的 1:1 物理快照"""
        db_path = r"D:/Dev/autoplay/config/calibration_db.json"
        dock_rect = None
        if os.path.exists(db_path):
            with open(db_path, "r") as f:
                raw = json.load(f).get("dock_rect")
                # 转换 mss 格式
                dock_rect = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        # 执行抓取
        path = self.vc.capture_screen(region=dock_rect)
        save_path = os.path.join(self.records_dir, f"skill_msi_last_view.jpg")
        import shutil
        shutil.copy(path, save_path)
        print(f"[SKILL] 已记录当前实时快照: {save_path}")
        return save_path

    def click_input_thumbnail(self):
        """
        [已录制动作]: 寻找左上角 Inputs 地标并点击其下方的小图。
        包含自动截屏记录。
        """
        print("\n--- 执行技能: click_input_thumbnail ---")
        # 1. 自动截屏记录
        view_path = self.capture_standard_view()
        img = cv2.imread(view_path)
        
        # 2. 地标锚定
        context = self.ocr.read_screen(img)
        anchor_x, anchor_y = -1, -1
        for line in context.split('\n'):
            if "input" in line.lower():
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    anchor_x, anchor_y = int(parts[0]), int(parts[1])
                    print(f"[SKILL] 找到地标锚点: {line}")
                    break
                except: continue
        
        if anchor_y == -1:
            print("[SKILL] 错误: 未能在快照中定位地标文字，动作终止。")
            return False

        # 3. 物理全域点击 (使用 1:1 物理中心对齐)
        db_path = r"D:/Dev/autoplay/config/calibration_db.json"
        with open(db_path, "r") as f:
            base_x = json.load(f)['dock_rect']['x']
            base_y = json.load(f)['dock_rect']['y']
            
        # 默认下移 100 像素作为点击位 (或进行更复杂的 OpenCV 探测)
        target_abs_x = base_x + anchor_x
        target_abs_y = base_y + anchor_y + 120 # 根据实验得出的下探深度
        
        print(f"[SKILL] 点击执行位: ({target_abs_x}, {target_abs_y})")
        self.agent.click_at(target_abs_x, target_abs_y)
        return True

if __name__ == "__main__":
    skills = MSISkills()
    skills.click_input_thumbnail()
