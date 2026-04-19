import ctypes
import time
import sys
import pygetwindow as gw
import math

# 强制 DPI 感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

user32 = ctypes.windll.user32

def mouse_move(x, y):
    user32.SetCursorPos(x, y)

def mouse_click():
    # 模拟深度点击：按下 -> 停留 -> 弹起
    user32.mouse_event(2, 0, 0, 0, 0) # LEFTDOWN
    time.sleep(0.3)
    user32.mouse_event(4, 0, 0, 0, 0) # LEFTUP

def hardware_type_ultra_slow(text):
    import pydirectinput
    for char in text:
        print(f"正在键入: {char}")
        pydirectinput.press(char)
        time.sleep(1.0) # 极慢速，确保远程桌面响应

def circle_dance(cx, cy, radius=20, duration=3):
    """在目标点周围打圈，让用户看清准星"""
    print("正在执行可视化对齐检验（打圈）...")
    start_time = time.time()
    while time.time() - start_time < duration:
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            x = int(cx + radius * math.cos(rad))
            y = int(cy + radius * math.sin(rad))
            mouse_move(x, y)
            time.sleep(0.01)

def main():
    print("--- 启动【可视化准星确认】终极录入 ---")
    
    # 1. 定位
    target_win = None
    for w in gw.getAllWindows():
        if "oliver" in w.title.lower() and "chrome" in w.title.lower():
            target_win = w
            break
            
    if not target_win:
        print("ERROR: 未发现远程窗口！")
        return

    # 物理中心偏下
    real_x = target_win.left + target_win.width // 2
    real_y = target_win.top + 600
    
    print(f"锁定目标: {target_win.title}")
    print(f"物理基准: ({real_x}, {real_y})")

    # 2. 可视化校验：让用户看到我的准星
    circle_dance(real_x, real_y)
    
    # 3. 暴力点击获取焦点
    mouse_move(real_x, real_y)
    print("执行深压点击...")
    for _ in range(3):
        mouse_click()
        time.sleep(1)

    # 4. 终极尝试：先打个回车，再输入
    import pydirectinput
    pydirectinput.press('enter')
    time.sleep(1)
    
    print("开始极慢速灌注...")
    hardware_type_ultra_slow("123456")
    
    print("\n--- 任务结项 ---")

if __name__ == "__main__":
    main()
