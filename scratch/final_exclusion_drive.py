import sys
import os
import numpy as np
import cv2
from PIL import Image
import pydirectinput
import time

# 动态修正包搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.vision import VisionCapture

def heavy_type(text):
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 启动排除式视觉寻踪系统 (NO-URL-BAR Mode) ---")
    
    # 1. 视觉捕捉
    vision = VisionCapture()
    img_path = vision.capture_screen()
    img_np = np.array(Image.open(img_path))
    screen_w, screen_h = img_np.shape[1], img_np.shape[0]

    # 2. 深度指纹扫描
    ocr = vision.get_ocr()
    print("正在进行深度排重扫描，已屏蔽顶部 600 像素区域...")
    results = ocr.reader.readtext(img_np)
    
    target_pos = None
    
    # 策略：寻找在 Y 坐标大于 600 且 靠近横向中心位置的 Google 搜索框占位符
    best_prob = 0
    for (bbox, text, prob) in results:
        # 特征：同时包含“搜索”和“Google”或者是一长段中文提示词
        tx = int(np.mean([p[0] for p in bbox]))
        ty = int(np.mean([p[1] for p in bbox]))
        
        # 排除顶栏干扰 (Y > 600)
        if ty > 600 and 0.3 * screen_w < tx < 0.7 * screen_w:
            if any(kw in text for kw in ["搜索", "网址", "Google"]):
                if prob > best_prob:
                    best_prob = prob
                    target_pos = (tx, ty)
                    # 绘制最终瞄准框
                    cv2.rectangle(img_np, tuple(map(int, bbox[0])), tuple(map(int, bbox[2])), (0, 0, 255), 5)
                    print(f"绝杀锁定: '{text}' at {target_pos} (置信度: {prob:.2f})")

    if not target_pos:
        print("警告：指认失败，执行紧急保底策略（屏幕 2/3 高度位置）...")
        target_pos = (screen_w // 2, int(screen_h * 0.7))

    # 3. 结果存证
    final_img_path = r"D:\Dev\autoplay\records\FINAL_SEARCH_LOCK.jpg"
    os.makedirs(os.path.dirname(final_img_path), exist_ok=True)
    cv2.imwrite(final_img_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    print(f"最终瞄准存证已保存: {final_img_path}")

    # 4. 驱动执行
    print(f"正在前往终极坐标点 {target_pos} 进行物理穿透...")
    pydirectinput.moveTo(target_pos[0], target_pos[1], duration=1.0)
    # 三次连击激活输入框
    for _ in range(3):
        pydirectinput.click()
        time.sleep(0.5)
    
    time.sleep(1.0)
    heavy_type("123456")
    print("--- 物理灌注已完成 ---")

if __name__ == "__main__":
    main()
