# -*- coding: utf-8 -*-
import win32gui
import win32con
import logging

logger = logging.getLogger("WindowLock")

class WindowLock:
    def __init__(self, keyword="Tina"):
        self.keyword = keyword

    def find_window(self):
        found = []
        # 黑名单：绝对不能误抓的窗口关键词
        blacklist = ["antigravity", "visual studio", "code", ".json", ".py", "test_executor"]
        
        def cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                # 只有包含关键字且不在黑名单中，才认为是目标
                if self.keyword.lower() in title:
                    if not any(b in title for b in blacklist):
                        extra.append(hwnd)
            return True
        win32gui.EnumWindows(cb, found)
        return found[0] if found else None

    def lock_and_align(self, x=10, y=10, w=1440, h=900):
        """强制对齐并锁定窗口位置与样式"""
        hwnd = self.find_window()
        if not hwnd:
            logger.error(f"Could not find window with keyword '{self.keyword}' to lock.")
            return False

        # 1. 解除最大化（如果是最大化状态，位置无法固定）
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # 2. 强制移动并设置大小
        # SWP_NOSENDCHANGING: 不发送窗口大小改变消息，防止应用内部重排
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_SHOWWINDOW)
        
        # 3. 修改窗口样式：移除调整大小的边框和最大化按钮
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style &= ~win32con.WS_THICKFRAME  # 移除调整边框
        style &= ~win32con.WS_MAXIMIZEBOX # 移除最大化按钮
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        
        logger.info(f"Window '{self.keyword}' LOCKED at ({x}, {y}) with size {w}x{h}")
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    locker = WindowLock("Tina")
    locker.lock_and_align()
