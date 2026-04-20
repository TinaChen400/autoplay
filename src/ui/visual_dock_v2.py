import sys
import os
import io
import time
import traceback
import win32gui
import win32api
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QPushButton, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QPainter, QFont, QLinearGradient
import ctypes

# 强制开启物理像素感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except:
    ctypes.windll.user32.SetProcessDPIAware()

sys.path.append(r"D:\Dev\autoplay")
from src.utils.window_lock import WindowManager

class FlowStepCard(QFrame):
    def __init__(self, name, desc, index, parent=None):
        super().__init__(parent)
        self.name = name; self.status = "idle"
        self.setMinimumHeight(60)
        self.setObjectName("StepCard")
        self.setStyleSheet("#StepCard { background-color: rgba(35, 35, 40, 200); border: 1px solid rgba(255, 255, 255, 20); border-radius: 6px; }")
        
        v_layout = QVBoxLayout(self); v_layout.setContentsMargins(10,5,10,5)
        h_layout = QHBoxLayout()
        title = QLabel(name); title.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 13px; background: transparent;")
        self.status_ball = QFrame(); self.status_ball.setFixedSize(10, 10)
        h_layout.addWidget(title); h_layout.addStretch(); h_layout.addWidget(self.status_ball)
        v_layout.addLayout(h_layout)
        desc_lbl = QLabel(desc); desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 100); font-size: 10px;"); v_layout.addWidget(desc_lbl)
        self.update_status()

    def update_status(self):
        colors = {"idle": "#444", "running": "#ffd700", "success": "#00ff7f", "failed": "#ff4500"}
        self.status_ball.setStyleSheet(f"border-radius: 5px; background-color: {colors.get(self.status, 'gray')}; border: 1px solid white;")

class VisualDockV2(QWidget):
    def __init__(self):
        super().__init__()
        self.bridge = None 
        self.wm = WindowManager(["MSI", "Chrome"]) # 预初始化对位引擎
        self.panel_width_log = 260
        self.is_docked = False
        self.is_manual = False
        self.locked_hwnd = None
        self.detected_title = "已就绪"
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.overlay = QWidget(); layout.addWidget(self.overlay)
        self.init_panel(layout)
        
        self.timer = QTimer(); self.timer.timeout.connect(self.sync_logic); self.timer.start(300) # 提高到 3.3 FPS 追踪
        QTimer.singleShot(1000, self.lazy_load_brain)

    def init_panel(self, layout):
        self.panel = QFrame()
        self.panel.setFixedWidth(self.panel_width_log)
        self.panel.setStyleSheet("background-color: rgba(15, 15, 20, 250); border-left: 2px solid #00ff7f;")
        p_layout = QVBoxLayout(self.panel); p_layout.setContentsMargins(15, 20, 15, 15)
        
        self.title_lbl = QLabel("MISSION HUD V14"); self.title_lbl.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 16px; margin-bottom: 20px;")
        p_layout.addWidget(self.title_lbl)
        
        self.card_layout = QVBoxLayout()
        p_layout.addLayout(self.card_layout)
        p_layout.addStretch()
        
        self.lbl_status = QLabel("Mode: Init..."); self.lbl_status.setStyleSheet("color: #888; font-size: 10px;")
        p_layout.addWidget(self.lbl_status)
        
        btn_quit = QPushButton("QUIT MISSION (ESC)"); btn_quit.setStyleSheet("background: #522; color: #fcc; padding: 10px; border-radius: 4px;")
        btn_quit.clicked.connect(self.close); p_layout.addWidget(btn_quit)
        layout.addWidget(self.panel)

    def lazy_load_brain(self):
        try:
            from src.execution.task_bridge import TaskBridge
            self.bridge = TaskBridge()
            self.lbl_status.setText(f"Brain: {self.bridge.steps[0].name if self.bridge.steps else 'Ready'}")
            self.rebuild_cards()
        except: self.lbl_status.setText("Brain: Error")

    def rebuild_cards(self):
        # 清除旧卡片
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.cards = []
        for i, step in enumerate(self.bridge.steps):
            c = FlowStepCard(step.name, step.description, i)
            c.mousePressEvent = lambda e, idx=i: self.bridge.run_step(idx, self.refresh)
            self.card_layout.addWidget(c)
            self.cards.append(c)

    def refresh(self):
        if self.bridge:
            for i, c in enumerate(self.cards): c.status = self.bridge.steps[i].status; c.update_status()
        self.update()

    def sync_logic(self):
        self.refresh()
        if self.is_manual: return
        
        try:
            # 动态检测当前屏幕缩放系数
            scale = self.screen().devicePixelRatio()
            
            # 对位追踪
            if self.locked_hwnd and win32gui.IsWindow(self.locked_hwnd):
                self.wm.hwnd = self.locked_hwnd
            else: self.locked_hwnd = None
            
            rect = self.wm.get_window_rect()
            if rect:
                l, t, w, h = rect['left'], rect['top'], rect['width'], rect['height']
                # 转换物理坐标为逻辑坐标 (核心修正)
                log_l, log_t = int(l/scale), int(t/scale)
                log_w, log_h = int(w/scale), int(h/scale)
                
                # 同步 UI 尺寸与位置
                self.move(log_l, log_t)
                self.setFixedSize(log_w + self.panel_width_log, log_h)
                self.overlay.setFixedSize(log_w, log_h)
                self.is_docked = True; self.detected_title = rect['title']
            else:
                self.is_docked = False; self.detected_title = "等待窗口..."
        except: pass
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.overlay.geometry()
        # 只要吸附上就变绿，明确反馈
        status_color = QColor(0, 255, 127, 240) if self.is_docked else QColor(0, 191, 255, 100)
        painter.setPen(QPen(status_color, 3)); painter.drawRect(r.adjusted(2, 2, -2, -2))
        
        painter.setBrush(QColor(0,0,0,160)); painter.setPen(Qt.PenStyle.NoPen); painter.drawRect(r.x(), r.height()-30, r.width(), 30)
        painter.setPen(QPen(Qt.GlobalColor.white)); painter.setFont(QFont("Consolas", 8))
        tag = "[LOCKED]" if self.locked_hwnd else "[AUTO]"
        painter.drawText(r.adjusted(10, 0, -10, -5), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, f"{tag} {self.detected_title}")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: 
            self.old_p = e.globalPosition().toPoint(); self.is_manual = True
            
    def mouseMoveEvent(self, e):
        if hasattr(self, 'old_p') and self.old_p:
            d = e.globalPosition().toPoint() - self.old_p; self.move(self.x() + d.x(), self.y() + d.y()); self.old_p = e.globalPosition().toPoint()
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape: self.close()
        elif e.key() == Qt.Key.Key_Space:
            self.lock_under_hud()

    def lock_under_hud(self):
        scale = self.screen().devicePixelRatio()
        geom = self.overlay.geometry()
        cp = self.mapToGlobal(geom.center())
        found = win32gui.WindowFromPoint((int(cp.x()*scale), int(cp.y()*scale)))
        while win32gui.GetParent(found): found = win32gui.GetParent(found)
        if found and found != int(self.winId()):
            self.locked_hwnd = found; self.is_manual = False
            print(f"[HUD] Locked HWND: {self.locked_hwnd}")

if __name__ == "__main__":
    try:
        app = QApplication(app_args := sys.argv)
        app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        window = VisualDockV2()
        window.show()
        sys.exit(app.exec())
    except Exception:
        with open("crash.log", "w") as f: f.write(traceback.format_exc())
        print(traceback.format_exc())
