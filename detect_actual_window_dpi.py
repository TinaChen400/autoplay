import win32gui
import ctypes
import cv2
import numpy as np
from PIL import ImageGrab
import os

# 强制开启 DPI 感知，获取物理屏幕像素级的真实坐标！
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except:
    ctypes.windll.user32.SetProcessDPIAware()

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
        # GetWindowRect 获取包含了整个边框的窗口
        rect = win32gui.GetWindowRect(hwnd_target)
        x, y, r, b = rect
        w = r - x
        h = b - y
        
        # 尝试获取去除外部边框后的 Client 区域，这才是真正的网页/远程桌面内容区
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
    
    print(f"DPI感知后物理像素坐标 -> x: {x}, y: {y}, width: {w}, height: {h}")
    
    screen = ImageGrab.grab()
    img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
    
    # 画出准确的绿框
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 4)
    label = f'Actual Tina (X:{x}, Y:{y}, W:{w}, H:{h})'
    cv2.putText(img, label, (x + 10, y + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    
    # 绘制那4条硬编码的红线，看看在正确的缩放下是否能对齐
    COLUMN_X = {
        "Response A": 1249,
        "Response B": 1341,
        "Both Good": 1433,
        "Both Bad": 1507
    }
    for name, rel_x in COLUMN_X.items():
        abs_x = x + rel_x
        if abs_x < img.shape[1]:
            cv2.line(img, (abs_x, y), (abs_x, y + h), (0, 0, 255), 2)
            cv2.putText(img, name, (abs_x - 30, y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    out_dir = r"D:\Dev\autoplay\temp"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "dpi_aware_window_map.jpg")
    cv2.imwrite(out_path, img)
    print(f"准确的物理坐标截图已生成: {out_path}")
    os.startfile(out_path)

if __name__ == "__main__":
    main()
