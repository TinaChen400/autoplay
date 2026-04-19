import os
import sys
import json
import time
import pydirectinput
import cv2
import numpy as np

sys.path.append(r"D:\Dev\autoplay")
from src.utils.vision import VisionCapture

def find_ground_truth():
    print("--- 启动【物理对准：全屏绝对溯源】 ---")
    vc = VisionCapture()
    
    # 1. 抓取全屏 (获取真正的物理像素现状)
    print("正在进行全屏 OCR 深度扫描 (约需 5-8 秒)...")
    full_img_path = vc.capture_screen() # 默认截取全屏
    ocr = vc.get_ocr()
    image = cv2.imread(full_img_path)
    
    # 2. 寻找真正的 Google Logo
    pos = ocr.find_largest_element(image, "Google")
    if not pos:
        print("错误: 在全屏下也未找到 Google logo，请确认页面已显示。")
        return
    
    # 此时的 pos 就是全屏物理像素的 (X, Y)
    print(f"SUCCESS: Full screen trace found Google Logo at: {pos}")
    
    # 3. 计算输入框位址 (基于物理真相: pos[1] = 1172)
    # 根据之前的视觉偏差分析，我们将点击点设置在 Logo 下方 140 像素
    target_x = pos[0]
    target_y = pos[1] + 140
    
    print(f"ABS_PHYSICAL_TARGET: ({target_x}, {target_y})")
    
    # 4. 执行物理验证
    print("准备录入，请离手鼠标 (3s 倒计时)...")
    time.sleep(3)
    
    pydirectinput.moveTo(target_x, target_y)
    time.sleep(1)
    pydirectinput.click() # 此时鼠标应该已经在输入框内
    time.sleep(0.5)
    
    # 尝试多种录入保护
    pydirectinput.press('esc') # 退出可能的弹出框
    time.sleep(0.5)
    pydirectinput.click() # 再次激活
    
    test_str = "test me now ! "
    print(f"正在录入: {test_str}")
    for char in test_str:
        pydirectinput.typewrite(char)
        time.sleep(0.1)
    
    pydirectinput.press('enter')
    print("--- 溯源录入任务圆满完成！ ---")

if __name__ == "__main__":
    find_ground_truth()
