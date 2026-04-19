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
    print("--- 启动全域视觉寻踪系统 ---")
    
    # 1. 视觉捕捉
    vision = VisionCapture()
    img_path = vision.capture_screen()
    img_np = np.array(Image.open(img_path))
    print(f"当前全屏快照已就绪。")

    # 2. 地标指纹检索
    ocr = vision.get_ocr()
    print("正在扫描全屏地标指纹...")
    results = ocr.reader.readtext(img_np)
    
    target_pos = None
    target_text = ""
    
    # 在所有 OCR 结果中寻找最匹配的中心输入框
    screen_w, screen_h = img_np.shape[1], img_np.shape[0]
    
    for (bbox, text, prob) in results:
        if any(kw in text.lower() for kw in ["搜索", "网址", "google", "search"]):
            # 计算文字中心点
            tx = int(np.mean([p[0] for p in bbox]))
            ty = int(np.mean([p[1] for p in bbox]))
            
            # 过滤策略：排除屏幕最顶部的任务栏，且位于横向中心带
            if ty > 300 and 0.25 * screen_w < tx < 0.75 * screen_w:
                target_pos = (tx, ty)
                target_text = text
                # 绘制准星进行存证
                cv2.rectangle(img_np, tuple(map(int, bbox[0])), tuple(map(int, bbox[2])), (0, 0, 255), 3)
                print(f"锁定指纹: '{text}' at {target_pos}")
                break

    if not target_pos:
        print("警告：全域扫描未发现指纹，使用几何中心保底策略...")
        target_pos = (screen_w // 2, screen_h // 2 + 50)

    # 3. 存证：将最终准星保存到 D 盘
    check_path = r"D:\Dev\autoplay\records\full_scan_check.jpg"
    os.makedirs(os.path.dirname(check_path), exist_ok=True)
    cv2.imwrite(check_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    print(f"最终瞄准图已保存: {check_path}")

    # 4. 驱动执行
    print(f"正在对准目标点执行底层录入...")
    pydirectinput.moveTo(target_pos[0], target_pos[1], duration=1.0)
    pydirectinput.click()
    time.sleep(1.0)
    pydirectinput.click()
    time.sleep(1.5)
    
    heavy_type("123456")
    print("--- 全域寻踪任务执行完毕 ---")

if __name__ == "__main__":
    main()
