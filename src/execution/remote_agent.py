import os
import sys
import json
import time
import pydirectinput
import win32gui
import win32api
import win32con
import cv2

# Project paths
sys.path.append(r"D:\Dev\autoplay")
from src.utils.vision import VisionCapture

class RemoteAgent:
    """
    自适应远程桌面 Agent 核心库。
    具备多环境记忆能力 (Profiles) 与物理级交互接口。
    """
    def __init__(self, profile_name="default"):
        self.profile_name = profile_name
        self.config_dir = r"D:\Dev\autoplay\config"
        self.profiles_path = os.path.join(self.config_dir, "profiles.json")
        self.vc = VisionCapture()
        self.current_profile = {}
        
        os.makedirs(self.config_dir, exist_ok=True)
        self.load_profiles()

    def load_profiles(self):
        """从磁盘加载所有电脑的记忆"""
        if os.path.exists(self.profiles_path):
            with open(self.profiles_path, "r") as f:
                self.profiles = json.load(f)
        else:
            self.profiles = {}

    def save_profiles(self):
        """保存当前学习到的参数"""
        with open(self.profiles_path, "w") as f:
            json.dump(self.profiles, f, indent=4)

    def calibrate(self, machine_id="oliver"):
        """
        开启全屏自动校准，寻找该电脑的物理真相。
        """
        print(f"--- AUTO-CALIBRATION: Finding ground truth for '{machine_id}' ---")
        full_img_path = self.vc.capture_screen()
        ocr = self.vc.get_ocr()
        image = cv2.imread(full_img_path)
        
        pos = ocr.find_largest_element(image, "Google")
        if not pos:
            print("ERROR: Calibration failed - Landmark not found.")
            return False
        
        # 记录大脑参数
        self.profiles[machine_id] = {
            "last_seen_logo": pos,
            "dpi_offset_y": 140, # 经验值
            "last_updated": time.time()
        }
        self.save_profiles()
        print(f"SUCCESS: Profiles updated for {machine_id} at {pos}")
        return True

    def click_at(self, x, y):
        """执行硬件级物理点击"""
        print(f"ACTION: Hardware-clicking at physical {x}, {y}")
        pydirectinput.click(int(x), int(y))
        time.sleep(0.1)

    def type_at(self, text, machine_id="oliver"):
        """针对该电脑的地标进行精准录入"""
        p = self.profiles.get(machine_id)
        if not p:
            if not self.calibrate(machine_id): return
            p = self.profiles.get(machine_id)
            
        target_x = p["last_seen_logo"][0]
        target_y = p["last_seen_logo"][1] + p["dpi_offset_y"]
        
        print(f"ACTION: Typing '{text}' at physical {target_x}, {target_y}")
        pydirectinput.click(target_x, target_y)
        time.sleep(0.5)
        pydirectinput.press('esc') # 惯例清理
        pydirectinput.click(target_x, target_y)
        
        for char in text:
            pydirectinput.typewrite(char)
            time.sleep(0.1)
        pydirectinput.press('enter')

    def scroll_down(self, times=2):
        """执行鲁棒的页边距翻页"""
        print(f"ACTION: Robust scrolling down {times} times")
        # 直接使用屏幕左侧 Gutter 确保焦点安全
        gx, gy = 200, 1000 
        pydirectinput.click(gx, gy)
        time.sleep(0.3)
        for _ in range(times):
            pydirectinput.press('space')
            time.sleep(0.3)

if __name__ == "__main__":
    # 演示：一键初始化并执行
    agent = RemoteAgent()
    if agent.calibrate("Oliver"):
        agent.type_at("Agentic Workflow Success", "Oliver")
        time.sleep(2)
        agent.scroll_down(1)
