import ctypes
import time
import sys

# 必须声明 DPI 感知，确保抓取的物理坐标与执行坐标 1:1
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

def mouse_click():
    user32.mouse_event(2, 0, 0, 0, 0) # LEFTDOWN
    time.sleep(0.2)
    user32.mouse_event(4, 0, 0, 0, 0) # LEFTUP

def hardware_type(text):
    import pydirectinput
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 启动【人工引导】物理锁定录入 ---")
    print(" >>> 请在 5 秒钟内，将鼠标移至搜索框中心并停住别动！")
    
    for i in range(5, 0, -1):
        print(f"倒计时: {i}...")
        time.sleep(1)
    
    # 瞬间抽取“真理坐标”
    tx, ty = get_mouse_pos()
    print(f"\n[OK] 坐标锁定完毕: ({tx}, {ty})")
    
    # 强制执行
    print("正在该点执行物理聚焦...")
    for _ in range(3):
        mouse_click()
        time.sleep(0.5)
    
    print(f"正在录入: 123456")
    hardware_type("123456")
    
    print("\n--- 任务结项 ---")

if __name__ == "__main__":
    main()
