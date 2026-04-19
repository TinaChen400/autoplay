import os
import sys
import json
import time
import pydirectinput
import cv2
import numpy as np

# 确保 D 盘项目路径在系统路径中
sys.path.append(r"D:\Dev\autoplay")

from src.utils.vision import VisionCapture

def run_vision_pilot(target_string="test me now ! "):
    print(f"--- 开启视觉引导录入任务: '{target_string}' ---")
    
    # 1. 加载对齐底座
    db_path = r"D:\Dev\autoplay\config\calibration_db.json"
    if not os.path.exists(db_path):
        print("错误: 未找到对齐底座 (calibration_db.json)，请先启动视觉相框进行对齐。")
        return
    
    with open(db_path, "r") as f:
        config = json.load(f)
    
    if config.get("status") != "docked":
        print("警告: 相框当前未处于‘锁定’状态，建议重新对齐。")
        # 我们依然尝试继续，使用最后的坐标
        
    dock = config["dock_rect"]
    # mss 格式: {'top': x, 'left': y, 'width': w, 'height': h}
    roi = {
        "top": dock["y"],
        "left": dock["x"],
        "width": dock["width"],
        "height": dock["height"]
    }
    
    # 2. 视觉采集与地标识别
    vc = VisionCapture()
    print("正在抓取副屏画面并进行 OCR 分析...")
    img_path = vc.capture_screen(region=roi)
    
    ocr = vc.get_ocr()
    image = cv2.imread(img_path)
    
    # 寻找 Google 文字作为地标 (寻找最大面积的那个)
    print("正在寻找最大的 'Google' Logo 地标...")
    pos = ocr.find_largest_element(image, "Google")
    
    if not pos:
        print("错误: 在绿框内未找到 'Google' 文字，请确认远程页面已加载。")
        return
    
    # 3. 坐标熔炼：Local ROI -> Global Physical
    # pos 是相对于截图(绿框)的 (dx, dy)
    global_x = dock["x"] + pos[0]
    global_y = dock["y"] + pos[1] + 160 # 向下偏移 160 像素来到输入框
    
    print(f"TARGET LOCK: Google Landmark ({pos[0]}, {pos[1]}), Global Physical ({global_x}, {global_y})")
    
    # 4. 物理级喷射录入
    print("准备录入，请离手鼠标...")
    time.sleep(2) # 给用户 2 秒反应时间
    
    # 物理点击激活
    pydirectinput.click(global_x, global_y)
    time.sleep(1)
    
    # 逐字喷射，确保远程 Canvas 捕获
    for char in target_string:
        pydirectinput.typewrite(char)
        time.sleep(0.1) # 100ms 间距，极度稳健
    
    pydirectinput.press('enter')
    print("--- 录入任务圆满完成！ ---")

if __name__ == "__main__":
    run_vision_pilot()
