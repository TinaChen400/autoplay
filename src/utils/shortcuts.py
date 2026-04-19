from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

class GlobalShortcutListener(QObject):
    """
    全局快捷键监听模块。
    通过 pynput 实现底层键盘钩子，捕捉特定组合键并发出信号。
    """
    # 定义信号，由 main 控制中心接收
    approval_triggered = pyqtSignal()
    debug_toggled = pyqtSignal()
    task_pushed = pyqtSignal()
    model_switched = pyqtSignal()
    emergency_stop = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.listener = None
        # 定义组合键映射
        self.combinations = {
            '<ctrl>+<enter>': self.approval_triggered.emit,
            '<ctrl>+d': self.debug_toggled.emit,
            '<ctrl>+t': self.task_pushed.emit,
            '<ctrl>+m': self.model_switched.emit,
            '<esc>': self.emergency_stop.emit
        }

    def start(self):
        """开始监听线程"""
        # 使用 GlobalHotKeys 方便处理组合键
        self.listener = keyboard.GlobalHotKeys(self.combinations)
        self.listener.start()

    def stop(self):
        """停止监听"""
        if self.listener:
            self.listener.stop()
