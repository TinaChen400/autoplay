import win32gui
import cv2
import numpy as np
from PIL import ImageGrab
import os

def get_window_rect(window_title_substring):
    hwnd_target = None
    def callback(hwnd, extra):
        nonlocal hwnd_target
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if window_title_substring in title:
                hwnd_target = hwnd
    win32gui.EnumWindows(callback, None)
    
    if hwnd_target:
        rect = win32gui.GetWindowRect(hwnd_target)
        x, y, r, b = rect
        w = r - x
        h = b - y
        
        # 获取不包含系统标题栏的实际内容区 (Client Area) 坐标
        client_rect = win32gui.GetClientRect(hwnd_target)
        pt = win32gui.ClientToScreen(hwnd_target, (0, 0))
        client_x, client_y = pt
        client_w = client_rect[2]
        client_h = client_rect[3]
        
        return {
            "window": {"x": x, "y": y, "width": w, "height": h},
            "client": {"x": client_x, "y": client_y, "width": client_w, "height": client_h}
        }
    return None

def main():
    info = get_window_rect("Tina")
    if not info:
        print("未找到名为 Tina 的窗口")
        return
        
    client = info["client"]
    x, y, w, h = client["x"], client["y"], client["width"], client["height"]
    
    print(f"找到的实际坐标 -> x: {x}, y: {y}, width: {w}, height: {h}")
    
    # 截取全屏幕并绘制
    screen = ImageGrab.grab()
    img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
    
    # 画出准确的绿框
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
    label = f'Actual Tina (X:{x}, Y:{y}, W:{w}, H:{h})'
    cv2.putText(img, label, (x + 10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    
    # 在这个准确的基础上画红线验证列
    COLUMN_X = {
        "Response A": 1249,
        "Response B": 1341,
        "Both Good": 1433,
        "Both Bad": 1507
    }
    for name, rel_x in COLUMN_X.items():
        abs_x = x + rel_x
        if abs_x < img.shape[1]:  # 防止画到屏幕外
            cv2.line(img, (abs_x, y), (abs_x, y + h), (0, 0, 255), 2)
            cv2.putText(img, name, (abs_x - 30, y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    out_dir = r"D:\Dev\autoplay\temp"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "actual_window_map.jpg")
    cv2.imwrite(out_path, img)
    print(f"准确的坐标截图已生成: {out_path}")
    os.startfile(out_path)

if __name__ == "__main__":
    main()
