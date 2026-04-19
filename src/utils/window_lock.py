import pygetwindow as gw
from typing import Optional, Tuple, Dict

class WindowManager:
    """
    窗口锁定与环境管理模块，负责定位远程桌面窗口。
    """
    def __init__(self, keywords: list):
        self.keywords = keywords
        self.target_window = None

    def find_remote_window(self) -> Optional[gw.Win32Window]:
        """
        根据关键字寻找匹配的远程桌面窗口。
        """
        all_windows = gw.getAllWindows()
        for kw in self.keywords:
            for win in all_windows:
                if kw and kw.lower() in win.title.lower():
                    # 额外检查：忽略 Agent 自己的窗口
                    if "AI Agent Overlay" in win.title:
                        continue
                    self.target_window = win
                    return win
        return None

    def get_window_rect(self) -> Optional[Dict[str, int]]:
        """
        获取目标窗口的坐标和宽高。
        """
        if not self.target_window:
            self.find_remote_window()
        
        if self.target_window:
            try:
                # 检查窗口是否还有效
                if not self.target_window.isActive:
                    pass # 仅作为存活检查
                return {
                    "left": self.target_window.left,
                    "top": self.target_window.top,
                    "width": self.target_window.width,
                    "height": self.target_window.height,
                    "title": self.target_window.title
                }
            except Exception:
                self.target_window = None
        return None

    def is_window_valid(self) -> bool:
        """
        检查当前锁定的窗口是否仍然有效且可见。
        """
        if self.target_window:
            try:
                return self.target_window.visible and not self.target_window.isMinimized
            except Exception:
                return False
        return False
