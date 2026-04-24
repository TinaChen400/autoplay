import os
import sys
import json
import time
import pydirectinput
import win32gui
import win32api
import win32con
import cv2
import random

# Project paths
sys.path.append(r"D:\Dev\autoplay")
from src.vision.capture import VisionCapture

from src.drivers.ahk_executor import AHKExecutor

class RemoteAgent:
    def __init__(self, profile_name="Tina"):
        self.profile_name = profile_name
        self.config_dir = r"D:\Dev\autoplay\config"
        self.profiles_path = os.path.join(self.config_dir, "profiles.json")
        self.vc = VisionCapture()
        self.profiles = {}
        
        # 初始化 AHK 执行器作为穿透备选 (优先检查 64 位路径)
        ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
        if not os.path.exists(ahk_exe):
            ahk_exe = r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
        self.ahk = AHKExecutor(ahk_path=ahk_exe)
        
        os.makedirs(self.config_dir, exist_ok=True)
        self.load_profiles()

    def press_key_via_ahk(self, key_name: str):
        """利用 AHK 的底层驱动能力发送按键"""
        # AHK 的方向键格式为 {Up}, {Down} 等
        ahk_key = f"{{{key_name.capitalize()}}}"
        print(f"ACTION: Forcefully sending '{ahk_key}' via AHK...")
        self.ahk.execute_shortcut(ahk_key)

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

    def double_click_at(self, x, y):
        """执行硬件级物理双击"""
        print(f"ACTION: Hardware-double-clicking at physical {x}, {y}")
        pydirectinput.doubleClick(int(x), int(y))
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

    def activate_window(self, keyword: str):
        """将包含 keyword 的窗口置于前台，确保按键能被捕获"""
        def cb(hwnd, ctx):
            title = win32gui.GetWindowText(hwnd).lower()
            if keyword and keyword.lower() in title and win32gui.IsWindowVisible(hwnd):
                ctx.append(hwnd)
            return True
        found = []
        win32gui.EnumWindows(cb, found)
        if found:
            try:
                win32gui.SetForegroundWindow(found[0])
                time.sleep(0.3)
                print(f"[AGENT] Window activated: {win32gui.GetWindowText(found[0])}")
            except Exception as e:
                print(f"[AGENT] activate_window failed: {e}")
        else:
            print(f"[AGENT] No window found for keyword: '{keyword}'")

    def press_key_sequence(self, keys: list, interval=0.5, hold_time=0.2):
        """执行硬件级按键序列（V6 穿透增强版）"""
        # 预先激活窗口
        self.activate_window(self.profile_name)
        
        print(f"ACTION: Executing forceful key sequence: {keys}")
        for key in keys:
            # 随机化按下时间 (Hold Time)
            actual_hold = hold_time
            if isinstance(hold_time, (list, tuple)) and len(hold_time) == 2:
                actual_hold = random.uniform(float(hold_time[0]), float(hold_time[1]))
            elif isinstance(hold_time, str) and "-" in hold_time:
                try:
                    min_h, max_h = map(float, hold_time.split("-"))
                    actual_hold = random.uniform(min_h, max_h)
                except: pass

            pydirectinput.keyDown(key)
            time.sleep(actual_hold) 
            pydirectinput.keyUp(key)
            
            # 每按一个键都重新计算一次间隔时间，确保不重样 (V28.5)
            actual_interval = interval
            if isinstance(interval, (list, tuple)) and len(interval) == 2:
                actual_interval = random.uniform(float(interval[0]), float(interval[1]))
            elif isinstance(interval, str) and "-" in interval:
                try:
                    min_i, max_i = map(float, interval.split("-"))
                    actual_interval = random.uniform(min_i, max_i)
                except: pass
                
            print(f"  [KEY] '{key}' pressed (Hold: {actual_hold:.2f}s, Next Interval: {actual_interval:.2f}s)")
            time.sleep(actual_interval)

if __name__ == "__main__":
    # 演示：一键初始化并执行
    agent = RemoteAgent()
    if agent.calibrate("Oliver"):
        agent.type_at("Agentic Workflow Success", "Oliver")
        time.sleep(2)
        agent.scroll_down(1)
