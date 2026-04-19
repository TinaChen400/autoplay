import sys
import os
import json
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QColor, QPen, QPainter
import pygetwindow as gw

class VisualDock(QWidget):
    def __init__(self):
        super().__init__()
        # 1. 窗口属性：无边框、工具悬浮、始终置顶
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 2. 初始状态
        self.resize(1000, 800)
        self.move(100, 100)
        self.is_docked = False
        self.target_title = "oliver"
        
        # 3. 颜色定义 (亮蓝 -> 绿色)
        self.default_color = QColor(0, 191, 255, 100) # DeepSkyBlue
        self.active_color = QColor(50, 205, 50, 150)   # LimeGreen
        self.current_color = self.default_color
        
        # 4. 定时器：每秒检测一次下方窗口
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_window_collision)
        self.timer.start(1000)
        
        # 5. 为了能拖动窗口
        self.old_pos = None

        print("--- 视觉相框已启动 ---")
        print(">>> 请将远程桌面窗口拖入此蓝色框内...")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 绘制边框 (高对比度亮蓝或绿色)
        pen = QPen(self.current_color, 8) # 加粗边框，方便对齐
        painter.setPen(pen)
        # 内部完全透明，只画边框
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(4, 4, -4, -4))
        
        # 2. 中心准星 (仅在未对齐时显示)
        if not self.is_docked:
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            cx, cy = self.width() // 2, self.height() // 2
            painter.drawLine(cx - 30, cy, cx + 30, cy)
            painter.drawLine(cx, cy - 30, cx, cy + 30)
            
            # 提示文字
            painter.setFont(self.font())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom, "正在寻找 oliver...")

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

    def check_window_collision(self):
        """核心：磁力吸附与碰撞检测"""
        try:
            target_win = None
            for w in gw.getAllWindows():
                if self.target_title in w.title.lower() and "chrome" in w.title.lower():
                    target_win = w
                    break
            
            if target_win:
                win_rect = QRect(target_win.left, target_win.top, target_win.width, target_win.height)
                dock_rect = QRect(self.x(), self.y(), self.width(), self.height())
                
                # 计算两个矩形的重叠程度或距离
                if dock_rect.intersects(win_rect):
                    if not self.is_docked:
                        # 🚨 触发全自动吸附：将相框坐标强制设定为窗口坐标
                        print(f"[SNAP] 啪嗒！相框已自动吸附至 {target_win.title}")
                        self.is_docked = True
                        self.current_color = self.active_color
                        # 像素级重合
                        self.setGeometry(win_rect)
                        self.update()
                        self.save_config()
                else:
                    if self.is_docked:
                        self.is_docked = False
                        self.current_color = self.default_color
                        print("[RELEASE] 相框已脱离。")
                        self.update()
        except Exception as e:
            pass

    def save_config(self):
        """保存当前相框坐标，供执行引擎调用"""
        config_path = r"D:\Dev\autoplay\config\calibration_db.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        data = {
            "dock_rect": {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height()
            },
            "status": "docked" if self.is_docked else "floating"
        }
        with open(config_path, "w") as f:
            json.dump(data, f, indent=4)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dock = VisualDock()
    dock.show()
    sys.exit(app.exec())
