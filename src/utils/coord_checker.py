import mss
import win32gui
import win32api
import ctypes
import json
import os

# 强制开启 DPI 感知以获取真实的物理数据
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

def check_geometry():
    print("--- 物理几何探测器 (DPI Aware) ---")
    
    # 1. 检测显示器硬件
    with mss.mss() as sct:
        print("\n[Monitor Detect]")
        for i, mon in enumerate(sct.monitors):
            print(f" Monitor {i}: {mon}")
            
    # 2. 检测当前的吸附配置
    db_path = r"D:\Dev\autoplay\config\calibration_db.json"
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            db = json.load(f)
            print(f"\n[Calibration DB] {db['dock_rect']}")
            
    # 3. 寻找当前 MSI 窗口的实时物理坐标
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "msi" in title.lower():
                rect = win32gui.GetWindowRect(hwnd)
                windows.append((title, rect))
        return True

    msi_windows = []
    win32gui.EnumWindows(callback, msi_windows)
    
    print("\n[Active MSI Windows]")
    for title, rect in msi_windows:
        print(f" Title: {title}")
        print(f" Phys Rect: {rect} (Left, Top, Right, Bottom)")
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        print(f" Phys Size: {width}x{height}")

if __name__ == "__main__":
    check_geometry()
