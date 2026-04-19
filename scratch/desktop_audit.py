import mss
import os
import ctypes
import numpy as np
import cv2
from PIL import Image

def audit_desktop():
    print("--- 启动全桌面物理审计 ---")
    
    # 1. 使用 mss 获取所有显示器信息
    with mss.mss() as sct:
        monitors = sct.monitors
        print(f"检测到 {len(monitors)-1} 个物理显示器。")
        for i, mon in enumerate(monitors):
            label = "全虚拟桌面" if i == 0 else f"显示器 {i}"
            print(f"{label}: Left={mon['left']}, Top={mon['top']}, Width={mon['width']}, Height={mon['height']}")
        
        # 捕捉全虚拟桌面截图 (monitor 0)
        shot = sct.shot(mon=0, output=r"D:\Dev\autoplay\temp\full_desktop.png")
        img_np = np.array(Image.open(shot))
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    # 2. 标记目标点 (906, 2572)
    # 注意：mss 的坐标系与 Windows 系统坐标系应当是对齐的
    tx, ty = 906, 2572
    
    # 虚拟桌面的偏移量（有些情况下 monitor 0 的坐标不是从 0,0 开始的）
    # 但通常 mss.shot(mon=0) 覆盖的是从虚拟桌面左上角开始的全图
    v_left = monitors[0]['left']
    v_top = monitors[0]['top']
    
    draw_x = tx - v_left
    draw_y = ty - v_top
    
    print(f"正在全虚拟桌面标注准星: ({tx}, {ty}) -> 绘图点: ({draw_x}, {draw_y})")
    
    # 画一个巨大的十字准星
    gap = 100
    cv2.line(img_bgr, (draw_x - gap, draw_y), (draw_x + gap, draw_y), (0, 0, 255), 5)
    cv2.line(img_bgr, (draw_x, draw_y - gap), (draw_x, draw_y + gap), (0, 0, 255), 5)
    cv2.circle(img_bgr, (draw_x, draw_y), 20, (0, 0, 255), -1)
    
    # 3. 保存审计结果
    audit_path = r"D:\Dev\autoplay\records\full_monitor_check.jpg"
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    cv2.imwrite(audit_path, img_bgr)
    print(f"\n>>>> [OK] 审计报告已生成：{audit_path}")
    print(">>>> 请您查看此图：如果红点没点在远程桌面上，请告诉我。")

if __name__ == "__main__":
    audit_desktop()
