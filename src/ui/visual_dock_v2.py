import sys
import os
import io
import time
import json
import traceback
import win32gui
import win32api
import win32con
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QPushButton, QSpacerItem, QSizePolicy, QComboBox, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QPainter, QFont, QLinearGradient
import ctypes

# 强物理对位模式：开启 DPI 感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except:
    ctypes.windll.user32.SetProcessDPIAware()

sys.path.append(r"D:\Dev\autoplay")
from src.utils.window_lock import WindowManager
from src.utils.hardware_manager import HardwareManager
from src.execution.task_bridge import TaskBridge

# --- 子组件：积木卡片 (现在在实心面板中，100% 响应) ---
class FlowStepCard(QFrame):
    def __init__(self, name, desc, index, bridge=None, refresh_cb=None, parent=None):
        super().__init__(parent)
        self.bridge = bridge; self.index = index; self.refresh_cb = refresh_cb; self.status = "idle"
        self.setMinimumHeight(90)
        self.setObjectName("StepCard")
        self.setStyleSheet("#StepCard { background-color: rgba(30,30,35, 255); border: 1px solid #444; border-radius: 8px; }")
        
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 8, 10, 8); layout.setSpacing(5)
        
        h_header = QHBoxLayout()
        self.status_ball = QFrame(); self.status_ball.setFixedSize(8, 8); self.update_status()
        h_header.addWidget(self.status_ball)
        
        self.title = QLabel(name); self.title.setStyleSheet("color: #eee; font-weight: bold; font-size: 11px; border:none;")
        h_header.addWidget(self.title)
        h_header.addStretch()
        
        # --- 核心交互区 ---
        def btn_style(bg): return f"background: {bg}; color: white; border: none; border-radius: 3px; font-size: 9px; padding: 3px 6px; font-weight: bold;"
        
        btn_run = QPushButton("RUN"); btn_run.setStyleSheet(btn_style("#2a2"))
        btn_run.clicked.connect(self.on_run_clicked)
        
        btn_aim = QPushButton("AIM"); btn_aim.setStyleSheet(btn_style("#a52"))
        btn_aim.clicked.connect(self.on_aim_clicked)
        
        h_header.addWidget(btn_run); h_header.addWidget(btn_aim)
        layout.addLayout(h_header)
        
        self.desc_lbl = QLabel(desc); self.desc_lbl.setWordWrap(True); self.desc_lbl.setStyleSheet("color: #888; font-size: 10px; border:none;")
        layout.addWidget(self.desc_lbl)
        
    def update_status(self):
        colors = {"idle": "#333", "running": "#ffd700", "success": "#00ff7f", "failed": "#ff4500"}
        self.status_ball.setStyleSheet(f"border-radius: 4px; background-color: {colors.get(self.status, '#333')}; border: none;")

    def on_run_clicked(self):
        print(f"[HUD-UI] 执行单步: {self.index}")
        if self.bridge:
            self.bridge.run_step(self.index, self.refresh_cb)

    def on_aim_clicked(self):
        # 抛出信号给主窗口进入瞄准模式
        parent_panel = self.window()
        if hasattr(parent_panel, 'start_aiming'):
            parent_panel.start_aiming(self.index)

# --- 窗口 A: 任务操作面板 (增加折叠功能解决遮挡问题) -------------------------------------------
class TaskControlPanel(QWidget):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.full_width = 360
        self.collapsed_width = 40
        self.panel_width = self.full_width
        self.is_collapsed = False
        self.drag_pos = None  # 用于实现独立窗口的物理拖拽
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setStyleSheet("""
            QWidget { background-color: #1a1a1e; border-left: 2px solid #00ff7f; font-family: 'Segoe UI', Arial; }
            QScrollBar:vertical { border: none; background: #222; width: 6px; margin: 0px; }
            QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QPushButton#toggle_btn { background: #2a2a2e; color: #00ff7f; border: 1px solid #3c3c3c; font-weight: bold; font-size: 14px; border-radius: 4px; }
            QPushButton#toggle_btn:hover { background: #3a3a3e; }
        """)
        self.init_ui()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
        
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 10, 8, 10); self.main_layout.setSpacing(10)
        
        # 顶部工具栏：折叠按钮 + 标题
        header_layout = QHBoxLayout()
        self.toggle_btn = QPushButton(">"); self.toggle_btn.setObjectName("toggle_btn")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_btn)
        
        self.header_title = QLabel("MISSION CONTROL")
        self.header_title.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 15px;")
        header_layout.addWidget(self.header_title)
        self.main_layout.addLayout(header_layout)
        
        # 包装器，用于折叠时隐藏下方所有内容
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(12)
        
        self.combo_mission = QComboBox()
        self.combo_mission.setStyleSheet("QComboBox { color: white; background: #2a2a2e; border: 1px solid #3c3c3c; padding: 6px; }")
        self.combo_mission.currentIndexChanged.connect(self.on_mission_change)
        self.content_layout.addWidget(self.combo_mission)
        
        # 正确时序：先创建滚动组件，再装入布局
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 5, 0); self.scroll_layout.setSpacing(10)
        self.scroll_area.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll_area)
        
        # 底部按钮区
        action_layout = QHBoxLayout()
        self.btn_reload = QPushButton("RELOAD")
        self.btn_run_all = QPushButton("START MISSION")
        for btn in [self.btn_reload, self.btn_run_all]:
            btn.setFixedHeight(35)
            btn.setStyleSheet("font-weight: bold; border-radius: 4px;")
            action_layout.addWidget(btn)
        
        self.btn_reload.clicked.connect(self.refresh_mission_data)
        self.btn_run_all.clicked.connect(self.on_run_all_clicked)
        self.btn_reload.setStyleSheet("background: #333; color: white;")
        self.btn_run_all.setStyleSheet("background: #00ff7f; color: black;")
        self.content_layout.addLayout(action_layout)
        
        # 将内容容器装入主布局
        self.main_layout.addWidget(self.content_container)
        self.refresh_mission_data()

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.panel_width = self.collapsed_width
            self.content_container.hide()
            self.header_title.hide()
            self.toggle_btn.setText("<")
        else:
            self.panel_width = self.full_width
            self.content_container.show()
            self.header_title.show()
            self.toggle_btn.setText(">")
        # 强制更新窗口宽度
        self.setFixedWidth(self.panel_width)

    def on_run_all_clicked(self):
        print("[UI] 启动全自动化 Scoring Mission...")
        if self.bridge:
            self.start_full_mission()

    def start_aiming(self, index):
        print(f"[UI] 积木 #{index} 进入瞄准模式...")
        # 实际逻辑可以调用 bridge.update_landmark_at_mouse

    def on_mission_change(self):
        m_name = self.combo_mission.currentText()
        if self.bridge and m_name:
            self.bridge.current_mission_name = m_name
            self.bridge.load_mission(m_name)
            self.rebuild_cards()

    def refresh_mission_data(self):
        if not self.bridge: return
        self.bridge.load_mission() 
        self.combo_mission.clear()
        self.combo_mission.addItems(self.bridge.all_mission_names)
        self.combo_mission.setCurrentText(self.bridge.current_mission_name)
        self.rebuild_cards()

    def rebuild_cards(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        for i, step in enumerate(self.bridge.steps):
            card = FlowStepCard(step.name, step.description, i, self.bridge, self.refresh_view)
            self.scroll_layout.addWidget(card)
        self.scroll_layout.addStretch()

    def refresh_view(self):
        # 刷新所有卡片的状态球
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), FlowStepCard):
                step = self.bridge.steps[item.widget().index]
                item.widget().status = step.status
                item.widget().update_status()

    def start_full_mission(self):
        self.bridge.run_mission(self.refresh_view)

        # 窗口 B: 幽灵边框图层 (100% 穿透) -------------------------------------------
class BorderOverlay(QWidget):
    def __init__(self, wm):
        super().__init__()
        self.wm = wm
        self.is_docked = False
        self.detected_title = "Searching..."
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 兼容性修正：改用更通用的穿透属性名
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        except:
            try:
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForInput, True)
            except: pass

    def paintEvent(self, event):
        if not self.is_docked: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 画外框
        pen = QPen(QColor(0, 255, 127, 200), 3)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width(), self.height())
        
        # 状态文字 (在左上角)
        painter.setPen(QColor(0, 255, 127))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(20, 30, f"DOCKING: {self.detected_title}")

# --- 主协调器 (负责同步两个窗口) ---
class DualHUDLauncher:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.bridge = TaskBridge()
        self.wm = WindowManager(["Tina", "Multimango", "Mango", "Chrome", "MSI", "SOURCE"])
        
        self.overlay = BorderOverlay(self.wm)
        self.panel = TaskControlPanel(self.bridge)
        self.panel_initial_docked = False # 记录是否已经完成过一次“开机自动对位”
        
        self.overlay.show()
        self.panel.show()
        
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_all)
        self.sync_timer.start(500)
        
    def sync_all(self):
        try:
            # 修正接口调用：从 find_target 改为 get_window_rect
            data = self.wm.get_window_rect()
            if data:
                self.overlay.is_docked = True
                self.overlay.detected_title = data["title"]
                
                # --- DPI 缩放补偿核心补丁 ---
                # Windows 返回的是物理像素，而 PyQt 在某些环境下需要逻辑像素
                screen = QApplication.primaryScreen()
                scale = screen.devicePixelRatio()
                
                # 物理像素转逻辑像素
                x = int(data["left"] / scale)
                y = int(data["top"] / scale)
                w = int(data["width"] / scale)
                h = int(data["height"] / scale)
                
                # 同步幽灵边框
                self.overlay.setGeometry(x, y, w, h)
                self.overlay.show()
                
                # --- 自由中心补丁：仅在启动第一次寻找目标时自动对位 ---
                if not self.panel_initial_docked:
                    px = x - self.panel.panel_width - 30
                    if px < 0: px = 10
                    self.panel.setGeometry(px, y, self.panel.panel_width, h)
                    self.view_follow_h = h # 记录基准高度
                    self.panel_initial_docked = True
                    print(f"[HUD] 首次对位完成，控制权已归还用户。当前物理坐标: {px}")
                else:
                    # 独立模式下，我们不再干涉面板的 XY 坐标，但依然保持它在显示状态
                    if self.panel.isHidden(): 
                        self.panel.show()
                
                # --- 核心改进：向执行引擎同步 [物理坐标]，向 UI 同步 [逻辑坐标] ---
                # 记住：Win32 API (点击/滚动) 必须使用物理像素（原始 data）
                curr_physical_rect = (data["left"], data["top"], data["width"], data["height"])
                if not hasattr(self, "_last_phys_rect") or self._last_phys_rect != curr_physical_rect:
                    # 我们修改 _save_dock_rect 让它保存物理值
                    self.bridge.skills._save_dock_rect(data["left"], data["top"], data["width"], data["height"])
                    self._last_phys_rect = curr_physical_rect
                    self._last_synced_rect = (x, y, w, h) # 仅作记录
            else:
                self.overlay.is_docked = False
                self.overlay.hide()
                # 强制重置 HWND 以便下次重新全桌扫描
                self.wm.hwnd = None 
                
                # 没找到目标时，面板停留在屏幕右侧中部，不消失
                screen = QApplication.primaryScreen().geometry()
                self.panel.setGeometry(screen.width() - self.panel.panel_width - 20, 
                                       screen.height() // 4, 
                                       self.panel.panel_width, 
                                       screen.height() // 2)
                self.panel.show()
        except Exception as e:
            print(f"[HUD-CRITICAL] 同步引擎发生严重错误: {e}")
            traceback.print_exc()
            
    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    launcher = DualHUDLauncher()
    launcher.run()
