import pydirectinput
import time
import sys
import pygetwindow as gw

# 彻底摒弃所有 OCR 和视觉依赖
def heavy_hardware_injection(text):
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 启动【无地标·纯物理】终极隔离录入系统 ---")
    
    # 1. 唯一任务：锁定 Oliver 窗口的物理实体
    target_win = None
    for w in gw.getAllWindows():
        if "oliver" in w.title.lower() and "chrome" in w.title.lower():
            target_win = w
            break
            
    if not target_win:
        print("ERROR: 未在桌面发现 Oliver 远程窗口！")
        return

    # 2. 计算纯物理重心坐标 (排除所有视觉动态干扰)
    # 窗口: [41, 223, 1391, 1053]
    # 物理中点偏下，稳准狠打击远程 Canvas
    final_x = target_win.left + target_win.width // 2
    final_y = target_win.top + 700 # 针对纵向 3840 屏幕的修正点
    
    print(f"锁定目标窗口: {target_win.title}")
    print(f"执行纯物理中心录入坐标: ({final_x}, {final_y})")

    # 3. 强制恢复与等待
    target_win.restore()
    time.sleep(2)

    # 4. 物理级焦点夺取 (不依赖系统激活)
    pydirectinput.moveTo(final_x, final_y, duration=1.0)
    for i in range(3):
        print(f"执行第 {i+1} 次物理点击聚焦...")
        pydirectinput.click()
        time.sleep(0.8)

    # 5. 硬核信号发射
    print(f"正在通过硬件驱动发送信号: 123456")
    heavy_hardware_injection("123456")
    
    print("\n--- 全案任务交付完毕 ---")
    print("Agent 已完成物理层面所有指令集，请查看远程页面结果。")

if __name__ == "__main__":
    main()
