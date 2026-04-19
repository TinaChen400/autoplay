import sys
import os
import json
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QPen, QPainter, QFont
import pygetwindow as gw
import win32gui
import win32con
import win32api
import ctypes

# 强力开启物理像素感知 (解决高 DPI 缩放截屏不全问题)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except:
    ctypes.windll.user32.SetProcessDPIAware()

# Project paths
sys.path.append(r"D:\Dev\autoplay")
from src.execution.remote_agent import RemoteAgent

class VisualDockV2(QWidget):
    def __init__(self):
        super().__init__()
        # 1. 注入 Agent 大脑
        self.agent = RemoteAgent()
        self.profile_list = list(self.agent.profiles.keys())
        self.profile_index = 0
        
        # 默认锁定
        if self.profile_list:
            self.target_title_keyword = self.profile_list[self.profile_index].lower()
        else:
            self.target_title_keyword = "oliver"
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resize(1000, 800)
        self.move(200, 200) # 初始位置略微偏移，防止挡住中心
        self.is_docked = False
        self.target_title_keyword = "oliver"
        self.detected_title = "正在寻找目标..."
        
        self.default_color = QColor(0, 191, 255, 120) # 亮蓝
        self.active_color = QColor(50, 255, 50, 180)   # 亮绿
        self.current_color = self.default_color
        
        # 键盘交互需要焦点
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_window_collision)
        self.timer.start(500) # 提高采样率到 0.5 秒
        
        self.old_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 边框
        pen_width = 10 if self.is_docked else 6
        painter.setPen(QPen(self.current_color, pen_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(5, 5, -5, -5))
        
        # 2. 状态信息
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        painter.setFont(font)
        
        status_text = f"目标: {self.target_title_keyword.upper()} | {self.detected_title}"
        if self.is_docked:
            status_text = f" [已锁定: {self.target_title_keyword.upper()}] {self.detected_title}"
            
        # 在底部绘制状态栏背景
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, self.height()-45, self.width(), 45)
        
        # 绘制文本
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(self.rect().adjusted(10, 0, -10, -5), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, status_text)
        
        # 绘制操作提示 (右下角)
        hint_font = QFont("Consolas", 8)
        painter.setFont(hint_font)
        painter.drawText(self.rect().adjusted(0, 0, -10, -5), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, "TAB:切机 | F5:重校")

        # 3. 中心准星 (未对齐时)
        if not self.is_docked:
            painter.setPen(QPen(self.default_color, 2))
            cx, cy = self.width() // 2, self.height() // 2
            painter.drawLine(cx - 40, cy, cx + 40, cy)
            painter.drawLine(cx, cy - 40, cx, cy + 40)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.save_config()

    def keyPressEvent(self, event):
        """交互快捷键：Tab 切机，F5 校准"""
        if event.key() == Qt.Key.Key_Tab:
            # 循环切换档案
            self.agent.load_profiles() # 实时刷新
            self.profile_list = list(self.agent.profiles.keys())
            if self.profile_list:
                self.profile_index = (self.profile_index + 1) % len(self.profile_list)
                self.target_title_keyword = self.profile_list[self.profile_index].lower()
                print(f"[HUD] 切换手动锁定目标: {self.target_title_keyword}")
                self.update()
        
        elif event.key() == Qt.Key.Key_F5:
            # 实时校准当前吸附的机器
            print(f"[HUD] 正在对当前机器 {self.target_title_keyword} 执行一键溯源...")
            self.agent.calibrate(self.target_title_keyword)
            # 视觉闪烁反馈
            self.current_color = QColor(255, 255, 255, 200)
            QTimer.singleShot(200, lambda: self.__setattr__('current_color', self.active_color))
            self.update()
        
        elif event.key() == Qt.Key.Key_Escape:
            # 优雅退出
            print("[HUD] 收到退出指令，正在关闭指挥中心...")
            self.close()
            
        elif event.key() == Qt.Key.Key_F6:
            # 【新功能】所见即所得截图
            print("[HUD] 正在拍照：截取当前相框覆盖区域...")
            self.capture_roi()

    def capture_roi(self):
        """直接截取当前 HUD 覆盖的区域"""
        try:
            screen = QApplication.primaryScreen()
            # 隐藏自己一瞬，防止拍到蓝框
            self.hide()
            QTimer.singleShot(100, self._do_capture)
        except Exception as e:
            print(f"截图失败: {e}")

    def _do_capture(self):
        screen = QApplication.primaryScreen()
        # 按照 HUD 自己的几何尺寸抓取
        pixmap = screen.grabWindow(0, self.x(), self.y(), self.width(), self.height())
        target = r"D:\Dev\autoplay\records\msi_frame_shot.jpg"
        pixmap.save(target, "JPG")
        print(f"--- [相框自拍成功] 已保存至: {target} ---")
        self.show()

    def check_window_collision(self):
        """核心：使用 win32gui 内核 API 强制对齐"""
        try:
            # 1. 精准寻找句柄 (HWND)
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if self.target_title_keyword in title.lower() and "chrome" in title.lower():
                        windows.append((hwnd, title))
                return True
            
            target_windows = []
            win32gui.EnumWindows(callback, target_windows)
            
            if target_windows:
                # 选取第一个匹配的
                hwnd, title = target_windows[0]
                self.detected_title = title
                
                # 2. 抓取内核级物理像素矩形 (绝对准)
                rect = win32gui.GetWindowRect(hwnd)
                # rect = (left, top, right, bottom)
                win_rect = QRect(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                dock_rect = QRect(self.x(), self.y(), self.width(), self.height())
                
                # 3. 磁力判定与【动态追随】
                if dock_rect.intersects(win_rect):
                    # 🚨 核心增强：只要是吸附状态，每一帧都强制对齐（动态追随）
                    if not self.is_docked:
                        print(f"[KERNEL-FOLLOW] 发现目标 {title}，开启动态追随模式")
                        self.is_docked = True
                        self.current_color = self.active_color
                    
                    # 无论是否是刚吸附，只要坐标或大小对不上，就强制矫正
                    # 为了平滑，只要偏差大于 2 像素就更新
                    if abs(self.x() - rect[0]) > 2 or abs(self.width() - (rect[2]-rect[0])) > 2:
                        win32gui.SetWindowPos(
                            int(self.winId()), 
                            win32con.HWND_TOPMOST, 
                            rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1], 
                            win32con.SWP_NOACTIVATE
                        )
                        self.update()
                        self.save_config()
                else:
                    if self.is_docked:
                        self.is_docked = False
                        self.current_color = self.default_color
                        print("[RELEASE] 已脱离吸附区域。")
                        self.update()
            else:
                self.detected_title = f"未发现 {self.target_title_keyword} 窗口"
                if self.is_docked:
                    self.is_docked = True # 保持吸附颜色，但标记未发现
                    self.detected_title = "窗口可能已最小化或被遮挡"
                    self.update()
                    
        except Exception as e:
            print(f"Error in collision detection: {e}")
            pass

    def save_config(self):
        config_path = r"D:\Dev\autoplay\config\calibration_db.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 🚨 核心修正：使用物理像素保存，确保截图库 100% 对齐
        rect = win32gui.GetWindowRect(int(self.winId()))
        phys_rect = {
            "x": rect[0], 
            "y": rect[1], 
            "width": rect[2] - rect[0], 
            "height": rect[3] - rect[1]
        }
        
        data = {
            "dock_rect": phys_rect,
            "status": "docked" if self.is_docked else "floating",
            "last_target": self.target_title_keyword
        }
        with open(config_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[HUD] 物理坐标档案已同步: {phys_rect}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dock = VisualDockV2()
    dock.show()
    sys.exit(app.exec())
