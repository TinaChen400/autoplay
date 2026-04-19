import cv2
import numpy as np
import os
import sys
from PIL import Image

# 修复模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.vision import VisionCapture

def main():
    print("--- 启动准星实测程序 ---")
    
    # 1. 实时捕捉
    vision = VisionCapture()
    img_path = vision.capture_screen()
    img_pil = Image.open(img_path)
    img_np = np.array(img_pil)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    # 2. OCR 寻踪
    ocr = vision.get_ocr()
    print("正在进行全屏指纹扫描...")
    results = ocr.reader.readtext(img_np)
    
    target_pos = None
    target_text = ""
    
    # 寻找网页中心的指纹
    for (bbox, text, prob) in results:
        if any(keyword in text for keyword in ["搜索", "网址", "Search", "Google"]):
            tx = int((bbox[0][0] + bbox[2][0]) / 2)
            ty = int((bbox[0][1] + bbox[2][1]) / 2)
            # 过滤逻辑：屏幕中下部，横向中心
            screen_w = img_np.shape[1]
            if 0.3 * screen_w < tx < 0.7 * screen_w and ty > 400:
                target_pos = (tx, ty)
                target_text = text
                break

    if target_pos:
        print(f"准星已锁定地标: '{target_text}' 于 {target_pos}")
        # 画一个巨大的红十字
        tx, ty = target_pos
        gap = 40
        # 横线
        cv2.line(img_bgr, (tx - gap, ty), (tx + gap, ty), (0, 0, 255), 3)
        # 竖线
        cv2.line(img_bgr, (tx, ty - gap), (tx, ty + gap), (0, 0, 255), 3)
        # 画个圆圈关注
        cv2.circle(img_bgr, (tx, ty), 10, (0, 0, 255), -1)
    else:
        print("警告：全屏未发现指纹，将在屏幕中心画下标记供参考。")
        tx, ty = img_np.shape[1] // 2, img_np.shape[0] // 2
        cv2.line(img_bgr, (tx - gap, ty), (tx + gap, ty), (0, 255, 0), 2) # 用绿色代表保底

    # 3. 保存校验图到 D 盘
    save_path = r"D:\Dev\autoplay\records\final_aim_check.jpg"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cv2.imwrite(save_path, img_bgr)
    
    print("\n>>>> [OK] 准星校验图已成功保存：")
    print(f">>>> 路径: {save_path}")
    print(">>>> 请您打开此图片，查看红十字是否已经盖在搜索框正中央。")

if __name__ == "__main__":
    main()
