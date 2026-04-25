import win32gui
import win32process
import ctypes
import os
from ctypes import wintypes
from typing import Optional, Dict

# [回归稳定] 移除强制物理像素感知，允许回归系统默认的逻辑缩放 (如 1.25x)

class WindowManager:
    """
    DWM 级窗口像素管理模块。
    通过扩展框架边界 (Extended Frame Bounds) 实现绝对零误差对位。
    """
    def __init__(self, keywords: list = None):
        self.keywords = keywords if keywords else ["Tina"]
        self.hwnd = None
        self._frozen_rect = None # [V9.7] 绝对冻结坐标缓存

    def lock_window_to_size(self, w: int, h: int, x: int = 10, y: int = 10) -> bool:
        """
        [V6.1] 强力锁定：遍历所有关键字寻找目标，移除边框并强制对齐。
        """
        from src.drivers.window import WindowLock
        for kw in self.keywords:
            locker = WindowLock(keyword=kw)
            success = locker.lock_and_align(x, y, w, h)
            if success:
                self.hwnd = locker.find_window()
                return True
        return False

    def find_remote_window(self) -> Optional[int]:
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                
                # [V6.75 终极补丁] 进程级隔离：绝对禁止抓取属于本程序的窗口
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == os.getpid():
                    return True
                
                # 标题黑名单
                blacklist = ["antigravity", "control panel", "ai agent", "visual studio", "python", "debug", "doubao", "豆包"]
                if any(b in title for b in blacklist):
                    return True
                
                for kw in self.keywords:
                    if kw and kw.lower() in title:
                        l, t, r, b = win32gui.GetWindowRect(hwnd)
                        if (r - l) > 100 and (b - t) > 100: 
                            hwnds.append(hwnd)
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        if hwnds:
            # 强化逻辑：如果有多个同名窗口，优先选择 HWND 较大的（通常是更晚创建的活跃窗口）
            self.hwnd = sorted(hwnds, reverse=True)[0]
            return self.hwnd
        return None

    def get_window_rect(self) -> Optional[Dict[str, int]]:
        """
        [V9.95] 智能锁定：优先使用缓存，但允许在未完全吸附时动态刷新。
        """
        if self.hwnd:
            try:
                # 检查句柄是否有效
                if not win32gui.IsWindow(self.hwnd):
                    self.hwnd = None
                    return None

                rect = wintypes.RECT()
                DWMWA_EXTENDED_FRAME_BOUNDS = 9
                res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                    ctypes.wintypes.HWND(self.hwnd),
                    ctypes.wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
                    ctypes.byref(rect),
                    ctypes.sizeof(rect)
                )
                l, t, r, b = (rect.left, rect.top, rect.right, rect.bottom) if res == 0 else win32gui.GetWindowRect(self.hwnd)
                
                return {
                    "left": l, "top": t, "width": r - l, "height": b - t,
                    "title": win32gui.GetWindowText(self.hwnd)
                }
            except Exception:
                self.hwnd = None
        return None

    def is_window_valid(self) -> bool:
        if self.hwnd:
            return win32gui.IsWindowVisible(self.hwnd) and not win32gui.IsIconic(self.hwnd)

class WindowLock:
    """
    [V4.5] 窗口物理锁定引擎：
    负责移除窗口边框、最大化按钮，并强制对齐到指定物理坐标。
    """
    def __init__(self, keyword="Tina"):
        self.keyword = keyword

    def find_window(self):
        found = []
        # 黑名单：必须包含 'agent' 以防止锁定控制面板自身
        blacklist = ["agent", "antigravity", "visual studio", "code", ".json", ".py", "test_executor"]
        
        def cb(hwnd, extra):
            title = win32gui.GetWindowText(hwnd)
            if not title: return True
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            is_self = (pid == os.getpid())
            
            # 强化调试日志：打印每一个包含关键字的窗口，无论大小
            if self.keyword.lower() in title.lower():
                rect = win32gui.GetWindowRect(hwnd)
                w, h = rect[2] - rect[0], rect[3] - rect[1]
                print(f"[WINDOW_SCAN] 发现潜在目标: '{title}' | PID: {pid} | 尺寸: {w}x{h} | 是否自身: {is_self}")
                
                if not is_self:
                    # 排除已知的系统黑名单
                    blacklist = ["agent", "antigravity", "control", "visual studio", "python", "debug"]
                    if not any(b in title.lower() for b in blacklist):
                        if w > 100 and h > 100:
                            extra.append((hwnd, title, w, h))
            return True
        win32gui.EnumWindows(cb, found)
        
        if found:
            # 如果有多个，优先选面积最大的那个（通常是主显示窗口）
            found.sort(key=lambda x: x[2] * x[3], reverse=True)
            hwnd, title, w, h = found[0]
            print(f"[DEBUG] WindowLock Selected Main Window: '{title}' ({w}x{h}) HWND: {hwnd}")
            return hwnd
        return None

    def lock_and_align(self, x=10, y=10, w=1440, h=900):
        """强制对齐并锁定窗口位置与样式"""
        import win32con
        hwnd = self.find_window()
        if not hwnd:
            return False

        # 1. 解除最大化并准备修改样式
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # 2. [V5.3] 激进样式锁定：彻底移除标题栏、边框、最大化样式
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        # 移除标题栏 (WS_CAPTION), 边框 (WS_THICKFRAME), 最小/最大化按钮, 以及最大化状态 (WS_MAXIMIZE)
        style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX | win32con.WS_MAXIMIZE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        
        # 3. [V5.6] 暴力强推模式：连续发送位置指令并强制置顶
        import win32con
        for i in range(10):
            # 尝试两种不同的移动 API 以提高成功率
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, x, y, w, h, 
                                  win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED)
            ctypes.windll.user32.MoveWindow(hwnd, x, y, w, h, True)
            
            import time
            time.sleep(0.1)
        
        return True
