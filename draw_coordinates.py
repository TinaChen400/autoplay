import cv2
import json
import numpy as np
from PIL import ImageGrab
import os

def draw_coordinates():
    # 1. 截取全屏幕
    screen = ImageGrab.grab()
    img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
    
    # 2. 读取 calibration_db.json 获取坐标原点
    calib_path = r"D:\Dev\autoplay\config\calibration_db.json"
    try:
        with open(calib_path, "r", encoding="utf-8") as f:
            rect = json.load(f).get("dock_rect")
    except Exception as e:
        print(f"读取配置失败: {e}")
        return
        
    x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
    
    # 3. 绘制原点边界框 (黄色)
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), 3)
    cv2.putText(img, f"Origin (X:{x}, Y:{y})", (x + 10, y + 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    # 4. 绘制硬编码的 4 个选项列 (红色竖线)
    COLUMN_X = {
        "Response A": 1249,
        "Response B": 1341,
        "Both Good": 1433,
        "Both Bad": 1507
    }
    
    for name, rel_x in COLUMN_X.items():
        abs_x = x + rel_x
        # 画贯穿整个 dock 区域的竖线
        cv2.line(img, (abs_x, y), (abs_x, y + h), (0, 0, 255), 2)
        # 写上标签
        cv2.putText(img, f"{name}(+{rel_x})", (abs_x - 40, y + h - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        # 在顶部也写一个
        cv2.putText(img, name, (abs_x - 30, y + 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 5. 保存并输出
    out_dir = r"D:\Dev\autoplay\temp"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "visual_coordinate_map.jpg")
    cv2.imwrite(out_path, img)
    print(f"坐标系可视化图已生成: {out_path}")
    
    # 尝试自动打开图片（Windows 环境）
    os.startfile(out_path)

if __name__ == "__main__":
    draw_coordinates()
