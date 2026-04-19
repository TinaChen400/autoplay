import pydirectinput
import time
import sys

# 【唯一指令源】用户亲自校准的坐标
TARGET_X, TARGET_Y = 906, 2572

def strict_heavy_type(text):
    """
    最硬核的硬件驱动协议。
    不通过系统剪贴板，不通过软件模拟，只发送 RAW 扫描码。
    """
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print(f"--- 启动【用户绝对指令】录入程序 ---")
    print(f"当前锁定坐标: ({TARGET_X}, {TARGET_Y})")
    print("注意：本脚本已禁用所有 AI 和视觉纠偏，仅执行物理点击。")
    
    # 1. 物理到达
    pydirectinput.moveTo(TARGET_X, TARGET_Y, duration=1.0)
    
    # 2. 强力击穿 (三次连击)
    for i in range(3):
        print(f"正在进行第 {i+1} 次物理点击以夺取焦点...")
        pydirectinput.click()
        time.sleep(0.5)
    
    # 3. 硬件录入
    print("正在发射硬件信号: 123456")
    strict_heavy_type("123456")
    
    print("\n--- 指令执行完毕 ---")
    print("数字 123456 应该已录入到您刚才亲自点击的位置。")

if __name__ == "__main__":
    main()
