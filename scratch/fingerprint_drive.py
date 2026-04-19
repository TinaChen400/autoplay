import pydirectinput
import time
import os
import sys
import numpy as np
import cv2
from PIL import Image
import pygetwindow as gw

# 修复模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.vision import VisionCapture

def heavy_type(text):
    for char in text:
        pydirectinput.press(char)
        time.sleep(0.5)

def main():
    print("--- 视觉指纹终极打击 (Target: Center Search Bar) ---")
    
    # 1. 强力置顶
    target_win = None
    for w in gw.getAllWindows():
        if "oliver" in w.title.lower() and "chrome" in w.title.lower():
            target_win = w
            break
    if target_win:
        target_win.restore()
        target_win.activate()
        time.sleep(2)

    # 2. 视觉捕捉
    vision = VisionCapture()
    img_path = vision.capture_screen() # 强制存到 D:\Dev\autoplay\temp
    img_pil = Image.open(img_path)
    img_np = np.array(img_pil)
    
    # 3. 寻找搜索框内的“指纹”文字
    ocr = vision.get_ocr()
    print("正在搜找占位符: '在 Google 中搜索或输入网址'...")
    
    # 扩大搜索范围，寻找关键词
    results = ocr.reader.readtext(img_np)
    target_pos = None
    
    for (bbox, text, prob) in results:
        # 兼容中文或英文提示语
        if any(keyword in text for keyword in ["搜索", "网址", "Search", "Google"]):
            # 逻辑：寻找位于屏幕中心区域（横向 30%-70%）的文字
            tx = (bbox[0][0] + bbox[2][0]) / 2
            ty = (bbox[0][1] + bbox[2][1]) / 2
            screen_w = img_np.shape[1]
            if 0.3 * screen_w < tx < 0.7 * screen_w and ty > 400: # 排除顶部网址栏
                target_pos = (int(tx), int(ty))
                # 绘制准星图进行验证
                top_left = tuple(map(int, bbox[0]))
                bottom_right = tuple(map(int, bbox[2]))
                cv2.rectangle(img_np, top_left, bottom_right, (0, 0, 255), 3)
                print(f"锁定指纹文字: '{text}' at {target_pos}")
                break

    if not target_pos:
        print("警告：指纹识别失败，使用屏幕中心保底策略...")
        target_pos = (img_np.shape[1] // 2, img_np.shape[0] // 2 + 100)

    # 4. 保存准星图供用户核对 (D 盘专用)
    verify_path = r"D:\Dev\autoplay\records\target_lock.jpg"
    os.makedirs(os.path.dirname(verify_path), exist_ok=True)
    cv2.imwrite(verify_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    print(f"准星图已保存至: {verify_path} (请您核对红框位置)")

    # 5. 驱动执行
    print(f"正在对准红框中心执行硬件级录入...")
    pydirectinput.moveTo(target_pos[0], target_pos[1], duration=1.0)
    pydirectinput.click()
    time.sleep(1.0)
    pydirectinput.click()
    time.sleep(1.5)
    
    heavy_type("123456")
    print("--- 物理打桩录入完毕 ---")

if __name__ == "__main__":
    main()
