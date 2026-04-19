import pyautogui
import time
from typing import Optional

class PyExecutor:
    """
    基于 PyAutoGUI 的纯 Python 执行器。
    作为 AHK 缺失时的稳健备选。
    """
    def __init__(self, logger=None):
        self.logger = logger
        # 设置安全余量
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5 

    def log(self, msg, level="SYSTEM"):
        if self.logger:
            self.logger.log(level, msg)

    def execute_click(self, x: int, y: int):
        """物理点击：先移动再左击"""
        try:
            self.log(f"PyExecutor: 移动并点击 ({x}, {y})")
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
        except Exception as e:
            self.log(f"PyExecutor 点击异常: {e}", "ERROR")

    def execute_input(self, text: str):
        """物理输入：采用中英兼容的剪贴板粘贴模式"""
        try:
            import pyperclip
            import time
            clean_text = text.replace("{{Enter}}", "")
            self.log(f"PyExecutor: 采用剪贴板粘贴 -> {clean_text}")
            
            # 复制并执行 Ctrl+V (快速模式尝试)
            pyperclip.copy(clean_text)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.0) # 给远程粘贴留出充裕时间
            
            # 补发键盘模拟敲击 (慢速稳健模式 - 0.3秒一个字)
            self.log(f"PyExecutor: 正在以慢速(0.3s)模拟真实键盘录入...")
            pyautogui.write(clean_text, interval=0.3)
            
            # 如果带有回车标记则执行回车
            if "{{Enter}}" in text:
                time.sleep(0.3)
                pyautogui.press('enter')
                self.log("PyExecutor: 已补发 Enter 键")
        except Exception as e:
            self.log(f"PyExecutor 输入异常: {e}", "ERROR")

    def execute_shortcut(self, keys: str):
        """执行快捷键"""
        try:
            # 简单映射 "^r" 到 ctrl+r
            if keys == "^r":
                pyautogui.hotkey('ctrl', 'r')
            elif keys == "{F5}":
                pyautogui.press('f5')
            self.log(f"PyExecutor: 执行快捷键 {keys}")
        except Exception as e:
            self.log(f"PyExecutor 快捷键异常: {e}", "ERROR")

    def clear_page(self):
        """清空/重置远程页面（按 Esc）"""
        try:
            pyautogui.press('esc')
            self.log("PyExecutor: 已执行页面重置 (Esc)")
        except Exception as e:
            self.log(f"PyExecutor 重置异常: {e}", "ERROR")

    def test_physical(self):
        """物理自检：在屏幕中心画一个小圆圈"""
        try:
            w, h = pyautogui.size()
            cx, cy = w // 2, h // 2
            self.log("正在执行物理驱动自检 (划圆测试)...")
            pyautogui.moveTo(cx, cy, duration=0.5)
            # 划一个小正方形代表自检
            pyautogui.moveRel(50, 0, duration=0.2)
            pyautogui.moveRel(0, 50, duration=0.2)
            pyautogui.moveRel(-50, 0, duration=0.2)
            pyautogui.moveRel(0, -50, duration=0.2)
            return True
        except:
            return False
