import pydirectinput
import time
import os
import sys
import numpy as np
import cv2
from PIL import Image

# 修复模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.vision import VisionCapture

def hardware_tap(text):
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print(" --- 区域指纹寻踪引擎 (Seeker Mode) 启动 ---")
    
    # 1. 设置基准点 (真理像素)
    # 根据之前的 manual_calibration.json 读取，或硬编码
    hint_x, hint_y = 906, 2572
    print(f"基准中心点: ({hint_x}, {hint_y})")
    
    # 2. 局部大视野截屏 (600x600)
    vision = VisionCapture()
    # 注意：为了确保覆盖多显卡/多显示器，使用全屏捕捉后再裁剪
    full_img_path = vision.capture_screen()
    full_img = cv2.imread(full_img_path)
    
    h, w = full_img.shape[:2]
    radius = 300
    
    # 计算裁剪区域
    y1, y2 = max(0, hint_y - radius), min(h, hint_y + radius)
    x1, x2 = max(0, hint_x - radius), min(w, hint_x + radius)
    
    roi = full_img[y1:y2, x1:x2]
    print(f"局部侦察区域已建立: ({x1}, {y1}) 到 ({x2}, {y2})")

    # 3. 视觉特征检索 (OCR + 形态学)
    ocr = vision.get_ocr()
    print("正在局部区域内检索输入框指纹...")
    
    # 在局部区域执行 OCR
    results = ocr.reader.readtext(roi)
    
    final_target = (hint_x, hint_y) # 默认使用基准点
    found = False
    
    for (bbox, text, prob) in results:
        # 寻找常见的输入框特征文字
        if any(keyword in text for keyword in ["搜索", "网址", "Google", "Search", "Enter"]):
            # 计算局部坐标
            local_cx = int((bbox[0][0] + bbox[2][0]) / 2)
            local_cy = int((bbox[0][1] + bbox[2][1]) / 2)
            
            # 转换为全局坐标
            final_target = (x1 + local_cx, y1 + local_cy)
            found = True
            print(f"发现视觉修正点: '{text}' (置信度: {prob:.2f})")
            print(f"由 ({hint_x}, {hint_y}) 修正为 ({final_target[0]}, {final_target[1]})")
            
            # 绘图存档
            cv2.rectangle(roi, tuple(map(int, bbox[0])), tuple(map(int, bbox[2])), (0, 0, 255), 3)
            break

    # 4. 生成侦察报告图
    debug_path = r"D:\Dev\autoplay\records\seeker_debug.jpg"
    os.makedirs(os.path.dirname(debug_path), exist_ok=True)
    # 在原图画个十字表示您的原始点击位
    cv2.drawMarker(roi, (hint_x - x1, hint_y - y1), (255, 0, 0), cv2.MARKER_CROSS, 40, 2)
    cv2.imwrite(debug_path, roi)
    print(f"侦察报告已存至: {debug_path}")

    # 5. 驱动执行
    print("正在执行最终的驱动级录入...")
    pydirectinput.moveTo(final_target[0], final_target[1], duration=1.0)
    pydirectinput.click()
    time.sleep(1.0)
    pydirectinput.click()
    time.sleep(1.5)
    
    hardware_tap("123456")
    print("--- 任务执行完毕 ---")

if __name__ == "__main__":
    main()
