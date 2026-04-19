import pydirectinput
import time
import os

# 1. 准备本地舞台
target_file = r"D:\Dev\autoplay\temp\test_input.txt"
os.makedirs(os.path.dirname(target_file), exist_ok=True)
with open(target_file, "w") as f:
    f.write("--- 驱动级测试开启 ---\n")

# 2. 模拟真实录入节拍
def direct_type(text):
    for char in text:
        # pydirectinput 使用扫描码发送
        pydirectinput.press(char)
        time.sleep(0.5)

print("正在启动驱动级预演...")
time.sleep(2)

# 写入文件（模拟）
import subprocess
subprocess.Popen(['notepad.exe', target_file])
time.sleep(2)

print("正在尝试穿透录入...")
direct_type("123456")

print("预演结束。请检查记事本是否出现了 123456。")
