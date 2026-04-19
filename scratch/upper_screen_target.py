import sys
import os
import numpy as np
import cv2
from PIL import Image
import pydirectinput
import time
import pygetwindow as gw

# 修复模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.vision import VisionCapture

def heavy_type(text):
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 启动【上半屏】精准对齐录入系统 ---")
    
    # 1. 锁定 oliver 窗口位置
    target_win = None
    for w in gw.getWindowsWithTitle("oliver - Google Chrome"):
        target_win = w
        break
        
    if not target_win:
        print("警告：全屏未发现 'oliver' 窗口，将尝试全屏视觉搜寻...")
        # 降级：全屏扫描 Y < 1500 区域
    else:
        print(f"检测到窗口位置: {target_win.left, target_win.top, target_win.width, target_win.height}")

    # 2. 视觉定位
    vision = VisionCapture()
    img_path = vision.capture_screen()
    img_np = np.array(Image.open(img_path))
    
    ocr = vision.get_ocr()
    print("正在网页上半部扫描指纹...")
    results = ocr.reader.readtext(img_np)
    
    target_pos = None
    
    for (bbox, text, prob) in results:
        tx = int(np.mean([p[0] for p in bbox]))
        ty = int(np.mean([p[1] for p in bbox]))
        
        # 策略：锁定在屏幕上半部 (Y < 1500) 且包含关键词的区域
        if ty < 1500 and any(kw in text for kw in ["搜索", "网址", "Google"]):
            target_pos = (tx, ty)
            # 绘制准星
            cv2.rectangle(img_np, tuple(map(int, bbox[0])), tuple(map(int, bbox[2])), (0, 0, 255), 5)
            print(f"成功锁定上半屏目标: '{text}' at {target_pos}")
            break

    if not target_pos:
        print("警告：上半屏未发现地标，将使用窗口探测保底...")
        if target_win:
            target_pos = (target_win.left + target_win.width // 2, target_win.top + 600)
        else:
            target_pos = (1280, 800) # 终极保底

    # 3. 最终存证
    final_path = r"D:\Dev\autoplay\records\FINAL_UPPER_WIND.jpg"
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    cv2.imwrite(final_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    print(f"最终瞄准存证图: {final_path}")

    # 4. 驱动执行
    print(f"正在前往 {target_pos} 执行底层录入...")
    pydirectinput.moveTo(target_pos[0], target_pos[1], duration=1.0)
    pydirectinput.click()
    time.sleep(1.0)
    pydirectinput.click()
    time.sleep(1.5)
    
    heavy_type("123456")
    print("--- 上半屏任务执行完毕 ---")

if __name__ == "__main__":
    main()
