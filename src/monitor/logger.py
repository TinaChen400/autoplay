import time
import os
from PyQt6.QtCore import QObject, pyqtSignal

class SystemLogger(QObject):
    """
    日志与监控模块，支持分类记录执行、调试、模型与系统日志。
    支持 PyQt 信号，以便 UI 同步显示。
    """
    log_emitted = pyqtSignal(str, str) # category, message

    def __init__(self, log_dir: str = r"D:\Dev\autoplay\logs"):
        super().__init__()
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log(self, category: str, message: str):
        """
        记录日志。
        :param category: EXEC, DEBUG, MODEL, SYSTEM
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{category.upper()}] {message}\n"
        
        # 打印到控制台
        print(log_entry.strip())
        
        # 发射信号给 UI
        self.log_emitted.emit(category.upper(), message)
        
        # 写入文件
        file_path = os.path.join(self.log_dir, f"{category.lower()}.log")
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"日志写入失败: {e}")
