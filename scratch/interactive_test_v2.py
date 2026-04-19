import pyautogui
import time
import sys
import pygetwindow as gw

def heavy_type(text):
    for char in text:
        pyautogui.write(char)
        time.sleep(0.5)

# 1. 锁定并强制置顶 MSI/oliver 窗口
print("--- 强制焦点锁定开启 ---")
target_win = None
for w in gw.getAllWindows():
    if ("oliver" in w.title or "MSI" in w.title) and "Chrome" in w.title:
        target_win = w
        break

if target_win:
    print(f"检测到目标窗口: {target_win.title}")
    target_win.restore()
    target_win.activate()
    time.sleep(1.5)

# 2. 定位并深压点击 (使用之前的真理坐标)
target_x, target_y = 974, 3689
print(f"正在前往坐标 ({target_x}, {target_y}) 执行强力激活...")
pyautogui.moveTo(target_x, target_y, duration=1.0)
pyautogui.click()
time.sleep(1.0)
pyautogui.click()
time.sleep(1.0)

# 3. 进入静默输入期 (重要：停止控制台输出，防止焦点回弹)
print("\n[!!!] 脚本即将进入静默期，请确保 Chrome 已在前台，不要触碰任何按键 [!!!]")
print("倒计时 3 秒后开始录入...")
for i in range(3, 0, -1):
    print(f"READY: {i}")
    time.sleep(1)

# --- 静默输入区 ---
heavy_type("123456")
# -----------------

print("\n--- 录入指令执行完毕 ---")
print("如果仍然输入到了 VSCode，说明您的系统开启了‘控制台强行置顶’，请尝试将 VSCode 最小化后再试。")
