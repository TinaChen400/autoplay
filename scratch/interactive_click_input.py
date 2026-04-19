import ctypes
import time
import sys

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
    # 0x01 是鼠标左键的虚拟键码
    return user32.GetAsyncKeyState(0x01) & 0x8000

def hardware_type(text):
    import pydirectinput
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("\n" + "="*40)
    print("      【交互式哨兵】录入系统已激活")
    print("="*40)
    print("\n[READY] 哨兵正在严密监视鼠标左键...")
    print(" >>> 请您在【目标搜索框中心】点一下鼠标左键。")
    print(" >>> 此时请不要移动窗口或切换页面。")
    
    # 1. 持续监听点击
    target_pos = None
    try:
        while True:
            if is_left_clicked():
                # 捕获点击瞬间的坐标
                target_pos = get_mouse_pos()
                print(f"\n[DETECTED] 捕捉到您的指令点: {target_pos}")
                break
            time.sleep(0.01) # 高频采样以防漏掉点击
    except KeyboardInterrupt:
        print("\n[CANCELLED] 用户强制退出。")
        return

    # 2. 录入缓冲
    # 等待 1 秒，让 UI 相应您的那次点击
    time.sleep(1.0)
    
    # 3. 硬件执行
    print(f"正在该坐标发起硬件级脉冲录入: 123456")
    hardware_type("123456")
    
    print("\n" + "="*40)
    print("      指令已送达！任务圆满结项")
    print("="*40)

if __name__ == "__main__":
    main()
