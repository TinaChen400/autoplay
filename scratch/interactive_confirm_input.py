import ctypes
import time
import sys
import math

# 必须声明 DPI 感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

user32 = ctypes.windll.user32

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def is_left_clicked():
    return user32.GetAsyncKeyState(0x01) & 0x8000

def mouse_move(x, y):
    user32.SetCursorPos(x, y)

def mouse_wiggle(cx, cy, radius=15, duration=3):
    """在目标点疯狂晃动，让用户确认准星"""
    print(f"正在指认目标点 ({cx}, {cy})，请观察您的鼠标...")
    start_time = time.time()
    while time.time() - start_time < duration:
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x = int(cx + radius * math.cos(rad))
            y = int(cy + radius * math.sin(rad))
            mouse_move(x, y)
            time.sleep(0.02)
    mouse_move(cx, cy) # 回到中心

def hardware_type(text):
    import pydirectinput
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("\n" + "="*50)
    print("      【交互式·二次确认】录入系统已激活")
    print("="*50)
    print("\n[STEP 1] 哨兵正在等待您的点击指令...")
    print(" >>> 请在远程搜索框正中心点一下。")
    
    target_pos = None
    try:
        while True:
            if is_left_clicked():
                target_pos = get_mouse_pos()
                print(f"\n[STEP 2] 已捕获物理坐标: {target_pos}")
                break
            time.sleep(0.01)
    except KeyboardInterrupt:
        return

    # 关键步骤：指回给用户看
    print("\n[STEP 3] 正在回传可视化反馈，请确认鼠标位置...")
    mouse_wiggle(target_pos[0], target_pos[1])
    
    time.sleep(1.0)
    
    # 二次聚焦
    print("[STEP 4] 正在执行焦点锁定与录入...")
    for _ in range(3):
        user32.mouse_event(2, 0, 0, 0, 0) # DOWN
        time.sleep(0.2)
        user32.mouse_event(4, 0, 0, 0, 0) # UP
        time.sleep(0.5)
    
    hardware_type("123456")
    print("\n" + "="*50)
    print("      指令已注入！请查看远程端结果。")
    print("="*50)

if __name__ == "__main__":
    main()
