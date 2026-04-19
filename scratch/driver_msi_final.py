import pydirectinput
import time
import sys
import pygetwindow as gw

def hardware_tap(text):
    """
    底层扫描码录入协议。
    模拟物理键盘控制器直接发送信号。
    """
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

# 1. 真理位置锁死
abs_x, abs_y = 974, 3689
print(f"--- 驱动级实战启动 ---")
print(f"真理坐标确认: ({abs_x}, {abs_y})")

# 2. 暴力置顶与激活
try:
    for w in gw.getAllWindows():
        if ("oliver" in w.title or "MSI" in w.title) and "Chrome" in w.title:
            w.restore()
            w.activate()
            time.sleep(1.5)
            break
except:
    pass

# 3. 驱动级物理点击
print("正在执行驱动级强力聚焦...")
pydirectinput.click(abs_x, abs_y)
time.sleep(1.0)
pydirectinput.click(abs_x, abs_y)
time.sleep(2.0)

# 4. 驱动级物理击发
print("硬件信号发射中：123456...")
hardware_tap("123456")

print("\n--- 全案任务已完成 ---")
print("如果搜索框内仍没有文字，说明 RDP 可能在监听更底层的原始外设信号，那超出了软件模拟的范畴。")
print("请检查 MSi 网页的结果！")
