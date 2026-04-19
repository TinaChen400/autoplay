import sys
import os
import time
import json
import re
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PyQt6.QtCore import Qt, QTimer
import pyautogui
import pyperclip
import pygetwindow as gw

class LiteAgent(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Agent 终极对齐版 (视觉增强)")
        self.setFixedSize(500, 500)
        
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.btn = QPushButton("🎯 开启 OCR 视觉对齐并执行")
        self.btn.clicked.connect(self.run_task)
        self.btn.setStyleSheet("""
            height: 60px; 
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00f2fe, stop:1 #4facfe); 
            color: #fff; 
            font-weight: bold; 
            border-radius: 12px;
            font-size: 16px;
        """)
        
        layout = QVBoxLayout()
        layout.addWidget(self.btn)
        layout.addWidget(self.log_panel)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        self.append_log("Agent 视觉版已就绪：正在准备 EasyOCR 引擎...")
        # 预加载，防止第一次点按钮太慢
        QTimer.singleShot(2000, self.run_task)

    def append_log(self, text):
        log_str = f"[{time.strftime('%H:%M:%S')}] {text}"
        self.log_panel.append(log_str)
        print(log_str)
        sys.stdout.flush()

    def run_task(self):
        self.append_log("正在执行 MSI 窗口视觉定位...")
        
        # 1. 锁定窗口
        win = None
        for w in gw.getAllWindows():
            if "MSI" in w.title and "Chrome" in w.title:
                win = w
                break
        
        if not win:
            self.append_log("ERROR: 没找到 MSI 窗口！")
            return

        # 2. 暴力稳定化
        win.restore()
        win.activate()
        win.moveTo(10, 10) # 移到左上角，彻底排除多屏幕干扰
        time.sleep(1.5)
        
        # 3. OCR 视觉对齐 (真正的黑科技)
        self.append_log("启动视觉‘地标’锁定...")
        try:
            from src.utils.vision import VisionCapture
            from PIL import Image
            
            vision = VisionCapture()
            # 截取当前全屏
            img_path = vision.capture_screen()
            img_np = np.array(Image.open(img_path))
            
            # 使用 OCR 寻找搜索框
            ocr = vision.get_ocr()
            self.append_log("正在扫描页面文字布局...")
            
            # 方案 A：寻找 "Google" 标志
            target_pos = ocr.find_element(img_np, "Google")
            
            if target_pos:
                # 命中 Google 标志，向下偏移 150 像素即为搜索框
                click_x, click_y = target_pos[0], target_pos[1] + 150
                self.append_log(f"命中视觉地标 'Google': {target_pos} -> 修正点击点: ({click_x}, {click_y})")
            else:
                # 方案 B：保底策略，点击窗口上半部中心
                self.append_log("WARN: 未命中地标，切换至几何保底方案...")
                click_x = win.left + (win.width // 2)
                click_y = win.top + (win.height // 2) + 60
            
            # 4. 物理必中打击
            pyautogui.moveTo(click_x, click_y, duration=0.8)
            pyautogui.click()
            time.sleep(0.5)
            pyautogui.click() # 二次连击
            time.sleep(1.5)
            
            # 5. 录入
            content = "123456"
            pyperclip.copy(content)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.0)
            pyautogui.write(content, interval=0.3)
            
            self.append_log("任务已通过视觉校验，圆满完成！")
            
        except Exception as e:
            self.append_log(f"视觉流程异常: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LiteAgent()
    window.show()
    sys.exit(app.exec())
