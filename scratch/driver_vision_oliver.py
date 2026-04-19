import sys
import os

# 动态修正包搜索路径，确保能找到 D:\Dev\autoplay\src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pydirectinput
import time
import numpy as np
from PIL import Image
import pygetwindow as gw

def hardware_tap(text):
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 视觉地标精确打击 (Target: OLIVER) ---")
    
    # 1. 锁定窗口
    target_win = None
    for w in gw.getAllWindows():
        if "oliver" in w.title.lower() and "chrome" in w.title.lower():
            target_win = w
            break
            
    if not target_win:
        print("ERROR: 没找到标题包含 'oliver' 的 Chrome 窗口！")
        return

    # 2. 强力置顶
    target_win.restore()
    target_win.activate()
    time.sleep(2)
    
    # 3. 视觉捕捉
    from src.utils.vision import VisionCapture
    vision = VisionCapture()
    img_path = vision.capture_screen()
    img_np = np.array(Image.open(img_path))
    
    # 4. 寻找网页中心的 'Google' 标志作为地标
    ocr = vision.get_ocr()
    print("正在通过 OCR 检索网页中心的 Google 地标...")
    
    # 使用 OCRReader 自带的高级定位功能
    center_google = ocr.find_element(img_np, "Google")

    if not center_google:
        print("警告：未发现网页中心的 Google Logo，使用保底几何中心...")
        # 情况 B：保底点击窗口下部中心
        click_x = target_win.left + target_win.width // 2
        click_y = target_win.top + target_win.height // 2 + 100
    else:
        # 情况 A：地标锁定，向下偏移约 180 像素即为搜索框
        click_x, click_y = center_google[0], center_google[1] + 180
        print(f"地标锁定成功: {center_google} -> 搜索框目标: ({click_x}, {click_y})")

    # 5. 执行物理输入
    print(f"正在前往网页中心按钮进行驱动级录入...")
    pydirectinput.moveTo(click_x, click_y, duration=1.0)
    pydirectinput.click()
    time.sleep(1.0)
    pydirectinput.click()
    time.sleep(2.0)
    
    hardware_tap("123456")
    print("--- 精确录入指令执行完毕 ---")

if __name__ == "__main__":
    main()
