import pydirectinput
import time
import sys
import pygetwindow as gw

def heavy_type(text):
    """
    重型录入协议。
    0.5s 强制步进，确保穿透 RDP 通信层。
    """
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

# 1. 真理坐标载入
target_x, target_y = 906, 2572
print(f"--- 真理级物理录入启动 ---")
print(f"执行点: ({target_x}, {target_y})")

# 2. 暴力置顶隔离
try:
    for w in gw.getAllWindows():
        if ("oliver" in w.title.lower() or "msi" in w.title.lower()) and "chrome" in w.title.lower():
            w.restore()
            w.activate()
            time.sleep(1.5)
            break
except:
    pass

# 3. 驱动级物理点击
print("正在执行驱动级超压聚焦...")
pydirectinput.moveTo(target_x, target_y, duration=0.8)
pydirectinput.click()
time.sleep(1.0)
pydirectinput.click() # 二次连击确保焦点激活
time.sleep(2.0)

# 4. 驱动级物理击发
print("硬件扫描码发射中: 123456")
heavy_type("123456")

print("\n--- 录入完成 ---")
print("请检查您的浏览器中心搜索框！")
