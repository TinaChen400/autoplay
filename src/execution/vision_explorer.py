import cv2
import numpy as np
import os
import sys
import pydirectinput
import time

# Project paths
sys.path.append(r"D:\Dev\autoplay")

def hunt_smallest_item():
    print("--- 启动【视觉猎手：左上角最小块识别】 ---")
    img_path = r"D:\Dev\autoplay\records\msi_view.jpg"
    
    if not os.path.exists(img_path):
        print("错误: 未找到 MSI 截图文件")
        return

    # 1. 加载并进行图像预处理
    img = cv2.imread(img_path)
    height, width = img.shape[:2]
    
    # 锁定左上四分之一区域 (Top-Left Quadrant)
    roi_h, roi_w = height // 2, width // 2
    roi = img[0:roi_h, 0:roi_w]
    
    # 转为灰度并寻找轮廓
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    smallest_area = float('inf')
    target_center = None
    
    print(f"在左上区域探测到 {len(contours)} 个独立视觉块...")
    
    # 2. 这里的逻辑：寻找最小的、具有一定长宽比的块（排除单像素噪点）
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 5: # 排除极微小的噪点
            continue
            
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 往往图标是接近正方形的，且面积较小
        if area < smallest_area:
            smallest_area = area
            target_center = (x + w//2, y + h//2)
            # 记录详细数据便于确认
            best_box = (x, y, w, h)

    if target_center:
        tx, ty = target_center
        print(f"SUCCESS: Smallest target locked!")
        print(f"   - 位置: ({tx}, {ty})")
        print(f"   - 面积: {smallest_area} 像素")
        print(f"   - 尺寸: {best_box[2]}x{best_box[3]}")
        
        # 3. 执行物理点击 (需要加上 ROI 在全屏中的偏移，虽然 ROI 就在 (0,0) 开始)
        print("准备执行点击，请观察 MSI 屏幕 (2s 倒计)...")
        time.sleep(2)
        pydirectinput.click(tx, ty)
        print("--- 视觉打击指令执行完毕 ---")
    else:
        print("未能在该区域识别到明显的图形块。")

if __name__ == "__main__":
    hunt_smallest_item()
