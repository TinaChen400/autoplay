import os
import sys
import json
import time
import pydirectinput
import cv2
import numpy as np

sys.path.append(r"D:\Dev\autoplay")
from src.utils.vision import VisionCapture

def run_debug_pilot(target_string="test me now ! "):
    print("--- 启动【视觉透视】调试录入任务 ---")
    
    # 1. 加载底座
    db_path = r"D:\Dev\autoplay\config\calibration_db.json"
    with open(db_path, "r") as f:
        config = json.load(f)
    dock = config["dock_rect"]
    roi = {"top": dock["y"], "left": dock["x"], "width": dock["width"], "height": dock["height"]}
    
    # 2. 采集并分析
    vc = VisionCapture()
    img_path = vc.capture_screen(region=roi)
    ocr = vc.get_ocr()
    image = cv2.imread(img_path)
    
    # 查找地标
    pos = ocr.find_element(image, "Google")
    if not pos:
        print("错误: 未找到 Google 地标")
        return

    # 画布标记：我们要亲眼看看 Agent 的逻辑是否正确
    debug_img = image.copy()
    # 标注 Google 地标 (蓝色)
    cv2.circle(debug_img, (pos[0], pos[1]), 10, (255, 0, 0), -1)
    
    # 计算目标输入框中心 (红色)
    # 既然之前太高了，我们通过动态分析或增加偏移量尝试
    target_local_x = pos[0]
    target_local_y = pos[1] + 160 # 我们先看这个 160 在图里的什么位置
    cv2.circle(debug_img, (target_local_x, target_local_y), 15, (0, 0, 255), 5)
    
    # 保存调试图
    debug_path = r"D:\Dev\autoplay\temp\debug_aim.jpg"
    cv2.imwrite(debug_path, debug_img)
    print(f"--- 调试图已生成: {debug_path} ---")
    print(f"请检查图片里的【红点】是否刚好在搜索框中心。")
    
    # 映射为物理坐标
    global_x = dock["x"] + target_local_x
    global_y = dock["y"] + target_local_y
    
    print(f"物理攻击坐标(拟定): ({global_x}, {global_y})")
    
    # 为了验证，我们让鼠标移动过去但不点击，停留 3 秒
    pydirectinput.moveTo(global_x, global_y)
    print("鼠标已移动到拟定目标点，请观察它的位置是否正确...")
    time.sleep(3)

if __name__ == "__main__":
    run_debug_pilot()
