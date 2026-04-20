import win32gui
import ctypes
from ctypes import wintypes
from typing import Optional, Dict

# 全程开启物理像素感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

class WindowManager:
    """
    DWM 级窗口像素管理模块。
    通过扩展框架边界 (Extended Frame Bounds) 实现绝对零误差对位。
    """
    def __init__(self, keywords: list):
        self.keywords = keywords
        self.hwnd = None

    def find_remote_window(self) -> Optional[int]:
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                for kw in self.keywords:
                    if kw and kw.lower() in title:
                        # 排除 AI Agent 自身的透明窗口
                        if "ai agent" not in title and "visual" not in title:
                            hwnds.append(hwnd)
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        if hwnds:
            self.hwnd = hwnds[0]
            return self.hwnd
        return None

    def get_window_rect(self) -> Optional[Dict[str, int]]:
        """
        利用 DWM API 提取窗口真实的可见物理边框（不含阴影）。
        """
        if not self.hwnd:
            self.find_remote_window()
        
        if self.hwnd:
            try:
                # 获取 DWM 物理可见边界
                rect = wintypes.RECT()
                DWMWA_EXTENDED_FRAME_BOUNDS = 9
                res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                    ctypes.wintypes.HWND(self.hwnd),
                    ctypes.wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
                    ctypes.byref(rect),
                    ctypes.sizeof(rect)
                )
                
                if res != 0:
                    # 降级：如果 DWM 获取失败，使用常规模式
                    l, t, r, b = win32gui.GetWindowRect(self.hwnd)
                else:
                    l, t, r, b = rect.left, rect.top, rect.right, rect.bottom
                
                w = r - l
                h = b - t
                
                # 过滤异常值 (如最小化状态)
                if l < -10000 or t < -10000: return None
                    
                return {
                    "left": l,
                    "top": t,
                    "width": w,
                    "height": h,
                    "title": win32gui.GetWindowText(self.hwnd)
                }
            except Exception:
                self.hwnd = None
        return None

    def is_window_valid(self) -> bool:
        if self.hwnd:
            return win32gui.IsWindowVisible(self.hwnd) and not win32gui.IsIconic(self.hwnd)
        return False
