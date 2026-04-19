import ctypes
import time
import sys
import pygetwindow as gw

# 🚨 关键：声明 DPI 感知，防止 Windows 自动对坐标进行缩放偏移
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

def hardware_type(text):
    import pydirectinput
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 启动【DPI 全感知】物理对齐系统 ---")
    
    # 1. 重新获取窗口坐标 (在 DPI 觉醒状态下)
    target_win = None
    for w in gw.getAllWindows():
        if "oliver" in w.title.lower() and "chrome" in w.title.lower():
            target_win = w
            break
            
    if not target_win:
        print("ERROR: 未发现远程窗口！")
        return

    # 2. 计算物理真实坐标
    # 在觉醒模式下，这里的坐标应当与屏幕物理像素 1:1 对应
    real_x = target_win.left + target_win.width // 2
    # 远程桌面搜索框通常在顶部偏移 400-600 像素
    real_y = target_win.top + 600 
    
    print(f"DPI 觉醒后的窗口位置: {target_win.left, target_win.top}")
    print(f"物理目标点: ({real_x}, {real_y})")

    # 3. 底层硬件光标操纵 (绕过 pydirectinput 的二次缩放)
    print("正在强行接管硬件光标位置...")
    ctypes.windll.user32.SetCursorPos(real_x, real_y)
    
    # 4. 执行三次物理点击夺权
    time.sleep(1)
    # 使用 user32 直接发送点击事件
    user32 = ctypes.windll.user32
    for _ in range(3):
        user32.mouse_event(2, 0, 0, 0, 0) # MOUSEEVENTF_LEFTDOWN
        time.sleep(0.1)
        user32.mouse_event(4, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP
        print("物理点击聚焦中...")
        time.sleep(0.8)

    # 5. 发送扫描码
    print("正在发射硬件信号: 123456")
    hardware_type("123456")
    
    print("\n--- 任务执行完毕 ---")

if __name__ == "__main__":
    main()
