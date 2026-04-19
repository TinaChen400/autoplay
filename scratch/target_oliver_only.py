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
    print("--- 启动【oliver 窗口】专项隔离录入系统 ---")
    
    # 1. 物理锁定：寻找 Oliver 窗口
    target_win = None
    # 使用更宽松的模糊匹配
    for w in gw.getAllWindows():
        t = w.title.lower()
        if "oliver" in t and "chrome" in t:
            target_win = w
            break
        
    if not target_win:
        print("ERROR: 没找到标题包含 'Oliver' 的远程桌面窗口！")
        return

    print(f"锁定目标窗口: {target_win.title} at {target_win.left, target_win.top}")
    
    # 2. 强制窗口恢复（跳过不稳定的激活指令，通过点击夺权）
    target_win.restore()
    time.sleep(1.5)

    # 3. 视觉纠偏 (仅针对 oliver 窗口区域)
    vision = VisionCapture()
    img_path = vision.capture_screen()
    img_full = np.array(Image.open(img_path))
    
    # 裁剪出 oliver 窗口区域，彻底屏蔽本机干扰
    left, top, right, bottom = target_win.left, target_win.top, target_win.right, target_win.bottom
    # 稍微内缩，避开窗口边框和书签栏
    roi_crop = img_full[top+200:bottom-100, left+50:right-50]
    
    ocr = vision.get_ocr()
    print("正在 oliver 窗口内部检索远程搜索框指纹...")
    results = ocr.reader.readtext(roi_crop)
    
    target_pos = None
    
    for (bbox, text, prob) in results:
        if any(kw in text for kw in ["搜索", "网址", "Google"]):
            # 计算局部相对于 ROI 的坐标
            lcx = int((bbox[0][0] + bbox[2][0]) / 2)
            lcy = int((bbox[0][1] + bbox[2][1]) / 2)
            # 转换为全局坐标
            target_pos = (left + 50 + lcx, top + 200 + lcy)
            
            # 画图存证
            cv2.rectangle(img_full, (left+50+int(bbox[0][0]), top+200+int(bbox[0][1])), 
                          (left+50+int(bbox[2][0]), top+200+int(bbox[2][1])), (0, 0, 255), 5)
            print(f"隔离定位成功: '{text}' at {target_pos}")
            break

    if not target_pos:
        print("警告：oliver 窗口内部未发现指纹，使用窗口保底点...")
        target_pos = (target_win.left + target_win.width // 2, target_win.top + 600)

    # 4. 保存隔离瞄准图
    save_path = r"D:\Dev\autoplay\records\OLIVER_ONLY_LOCK.jpg"
    cv2.imwrite(save_path, cv2.cvtColor(img_full, cv2.COLOR_RGB2BGR))
    print(f"隔离瞄准图已保存: {save_path}")

    # 5. 执行物理录入
    print(f"正在向远程窗口 ({target_pos}) 发射物理信号...")
    pydirectinput.moveTo(target_pos[0], target_pos[1], duration=1.0)
    # 强力 3 连击夺回 Canvas 焦点
    for _ in range(3):
        pydirectinput.click()
        time.sleep(0.5)
    
    heavy_type("123456")
    print("--- oliver 专项任务执行完毕 ---")

if __name__ == "__main__":
    main()
