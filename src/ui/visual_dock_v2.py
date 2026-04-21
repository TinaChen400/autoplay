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
                             QLabel, QFrame, QPushButton, QSpacerItem, QSizePolicy, QComboBox, QScrollArea, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPen, QPainter, QFont, QLinearGradient
import ctypes

# 信号桥接器：解决跨线程 UI 刷新导致的崩溃 (V8)
class SignalBridge(QObject):
    step_added = pyqtSignal()
    # 视觉反馈信号：(x, y, w, h, type) 0=文字/红, 1=图标/绿 (V19)
    box_signal = pyqtSignal(int, int, int, int, int)

# --- V14 DWM 物理校准补丁 ---
DWMWA_EXTENDED_FRAME_BOUNDS = 9

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
        self.resizing = False # 是否正在调整大小
        self.resize_margin = 10 # 边缘检测范围
        self.user_touched = False # 用户是否手动干预过位置/大小
        
        self.setMouseTracking(True) # 开启鼠标追踪
        
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
            # 检查是否在底部边缘
            if event.position().y() >= self.height() - self.resize_margin:
                self.resizing = True
            else:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.user_touched = True # 标记用户已干预
            event.accept()

    def mouseReleaseEvent(self, event):
        self.resizing = False
        self.drag_pos = None

    def mouseMoveEvent(self, event):
        # 更新光标样式
        if event.position().y() >= self.height() - self.resize_margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.resizing:
                # 调整高度
                new_h = max(200, event.position().y())
                self.setFixedHeight(int(new_h))
            elif self.drag_pos is not None:
                # 移动窗口
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
        self.header_title.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 15px; border:none;")
        header_layout.addWidget(self.header_title)
        
        # 拖拽句柄提示
        handle = QLabel("⋮")
        handle.setStyleSheet("color: #444; font-size: 18px; margin-right: 5px;")
        header_layout.addWidget(handle)
        
        self.main_layout.addLayout(header_layout)
        
        # 包装器，用于折叠时隐藏下方所有内容
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(12)
        
        self.combo_mission = QComboBox()
        self.combo_mission.setStyleSheet("QComboBox { color: white; background: #2a2a2e; border: 1px solid #3c3c3c; padding: 6px; }")
        self.combo_mission.currentIndexChanged.connect(self.on_mission_change)
        
        # 任务控制工具栏 (V6 增强)
        mission_tools_layout = QHBoxLayout()
        mission_tools_layout.addWidget(self.combo_mission, 7)
        
        btn_style = "background: #333; color: #00ff7f; border: 1px solid #444; border-radius: 4px; font-weight: bold;"
        
        self.btn_add_mission = QPushButton("+")
        self.btn_add_mission.setFixedSize(26, 26)
        self.btn_add_mission.setStyleSheet(btn_style)
        self.btn_add_mission.setToolTip("创建新任务")
        self.btn_add_mission.clicked.connect(self.on_new_mission_clicked)
        mission_tools_layout.addWidget(self.btn_add_mission)
        
        self.btn_rename_mission = QPushButton("✎")
        self.btn_rename_mission.setFixedSize(26, 26)
        self.btn_rename_mission.setStyleSheet(btn_style)
        self.btn_rename_mission.setToolTip("重命名当前任务")
        self.btn_rename_mission.clicked.connect(self.on_rename_mission_clicked)
        mission_tools_layout.addWidget(self.btn_rename_mission)
        
        self.content_layout.addLayout(mission_tools_layout)
        
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
        
        # --- 录制核心按钮 ---
        self.btn_rec = QPushButton("REC")
        self.btn_rec.setFixedHeight(35)
        self.btn_rec.setFixedWidth(80)
        self.btn_rec.clicked.connect(self.on_rec_clicked)
        self.update_rec_button_style()
        action_layout.insertWidget(0, self.btn_rec) # 放在最左侧
        
        # --- 暴力诊断：测试按钮 (V16) ---
        self.btn_test = QPushButton("[TEST SIGNAL]")
        self.btn_test.setFixedHeight(30)
        self.btn_test.setStyleSheet("background: #552288; color: white; border-radius: 4px; font-weight: bold; font-size: 10px;")
        
        self.content_layout.addWidget(self.btn_test)
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

    def on_rec_clicked(self):
        if not self.bridge: return
        
        if not self.bridge.is_recording:
            # 开启录制前提示：是否作为新任务或覆盖现有任务？
            # 我们简化逻辑：如果是空白任务直接录制，否则询问
            self.bridge.start_recording()
            print("[UI] 录制模式已启动 (Yellow State)")
        else:
            self.bridge.stop_recording()
            print("[UI] 录制已保存 (Red State)")
        
        self.update_rec_button_style()
        self.rebuild_cards()

    def on_new_mission_clicked(self):
        name, ok = QInputDialog.getText(self, "新建任务", "请输入任务名称:")
        if ok and name:
            self.bridge.create_new_mission(name)
            self.refresh_mission_data()

    def on_rename_mission_clicked(self):
        name, ok = QInputDialog.getText(self, "重命名任务", "请输入新任务名称:", text=self.bridge.current_mission_name)
        if ok and name:
            self.bridge.rename_mission(name)
            self.refresh_mission_data()

    def update_rec_button_style(self):
        if not self.bridge: return
        
        if self.bridge.is_recording:
            # 录制中：黄色高亮
            style = "background: #ffd700; color: black; font-weight: bold; border-radius: 4px; border: 2px solid white;"
            self.btn_rec.setText("● REC...")
        else:
            # 未录制：醒目的深红色
            style = "background: #c0392b; color: white; font-weight: bold; border-radius: 4px; border: 1px solid #a93226;"
            self.btn_rec.setText("REC")
        
        self.btn_rec.setStyleSheet(style)

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
    def __init__(self, wm, bridge=None):
        super().__init__()
        self.wm = wm
        self.bridge = bridge
        self.is_docked = False
        self.detected_title = "Searching..."
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 兼容性修正：移除可能引起属性错误的实验性穿透设置
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # V11 视觉反馈属性
        self.feedback_rect = None
        self.feedback_timer = QTimer()
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self.clear_feedback)

    def draw_feedback(self, x, y, w, h, v_type=0):
        """显示短暂的视觉反馈框 (V12 强化调试版)"""
        if self.bridge:
            self.bridge._log(f"[UI] 收到视觉反馈信号: x={x}, y={y}, w={w}, h={h}")
        else:
            print(f"[UI] 收到视觉反馈信号: x={x}, y={y}, w={w}, h={h}")
            
        self.feedback_rect = QRect(x, y, w, h)
        self.feedback_timer.start(2000) # 持续 2 秒
        self.raise_() # 确保在最顶层
        self.update()

    def clear_feedback(self):
        self.feedback_rect = None
        self.update()

    def paintEvent(self, event):
        if not self.is_docked and not self.feedback_rect: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 如果处于对位状态，画绿色大外框
        if self.is_docked:
            pen = QPen(QColor(0, 255, 127, 200), 3)
            painter.setPen(pen)
            painter.drawRect(0, 0, self.width(), self.height())
            
            # 状态文字 (在左上角)
            painter.setPen(QColor(0, 255, 127))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(20, 30, f"DOCKING: {self.detected_title}")
        
        # 2. V11 录制即时反馈框 (V12-V19 强化显示)
        if self.feedback_rect:
            # V19/V21: 根据类型选择颜色 (0=红, 1=绿, 3=黄)
            if getattr(self, 'feedback_type', 0) == 3:
                color = QColor(255, 255, 0) # 黄色 (结构块)
            elif getattr(self, 'feedback_type', 0) == 1:
                color = QColor(0, 255, 127) # 绿色 (图标)
            else:
                color = QColor(255, 0, 0) # 红色 (文字)
            
            if self.feedback_rect.width() <= 20:
                # 绘制十字准星
                pen = QPen(color, 3)
                painter.setPen(pen)
                cx, cy = self.feedback_rect.center().x(), self.feedback_rect.center().y()
                painter.drawLine(cx - 15, cy, cx + 15, cy) # 水平线
                painter.drawLine(cx, cy - 15, cx, cy + 15) # 垂直线
                painter.drawEllipse(self.feedback_rect.center(), 10, 10) # 中心小圆
                
                painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                txt = "CLICKED" if getattr(self, 'feedback_type', 0) == 0 else "ICON SNAP"
                painter.drawText(cx + 15, cy - 15, txt)
            else:
                # 绘制识别框
                pen = QPen(color, 5) 
                painter.setPen(pen)
                painter.drawRect(self.feedback_rect)
                # 强化填充
                bg_color = QColor(255, 0, 0, 80) if getattr(self, 'feedback_type', 0) == 0 else QColor(0, 255, 127, 80)
                painter.fillRect(self.feedback_rect, bg_color)
                # 装饰性角标
                painter.setPen(color)
                painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                if getattr(self, 'feedback_type', 0) == 0:
                    label = "★ IDENTIFIED ★"
                elif getattr(self, 'feedback_type', 0) == 1:
                    label = "★ ANCHORED ★"
                else:
                    label = "★ UI BLOCK ★"
                painter.drawText(self.feedback_rect.left(), self.feedback_rect.top() - 10, label)

# --- 主协调器 (负责同步两个窗口) ---
class DualHUDLauncher:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.bridge = TaskBridge()
        self.wm = WindowManager(["Tina", "Multimango", "Mango", "Chrome", "MSI", "SOURCE"])
        
        self.overlay = BorderOverlay(self.wm, self.bridge)
        self.panel = TaskControlPanel(self.bridge)
        self.panel.btn_test.clicked.connect(self.on_manual_test_clicked)
        self.panel_initial_docked = False # 记录是否已经完成过一次“开机自动对位”
        
        # V15 DPI 缩放补偿核心
        screen = self.app.primaryScreen()
        self.dpi_scale = screen.devicePixelRatio()
        self.panel.header_title.setText(f"CONTROL (DPI: {self.dpi_scale}x)")
        self.bridge._log(f"[HUD] DPI 缩放检测完毕: {self.dpi_scale}x")
        
        # 建立实时录制反馈链路 (V8 线程安全版：利用信号槽机制)
        self.signal_bridge = SignalBridge()
        self.signal_bridge.step_added.connect(self.panel.rebuild_cards)
        self.signal_bridge.box_signal.connect(self.overlay.draw_feedback)
        
        self.bridge.on_step_added_cb = self.signal_bridge.step_added.emit
        # V15: 修改为使用逻辑像素转换代理
        self.bridge.on_visual_feedback_cb = self.on_visual_feedback_normalized
        
        self.overlay.show()
        self.panel.show()
        
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_all)
        self.sync_timer.start(500)

    def on_manual_test_clicked(self):
        """手动触发一个反馈框以验证 UI 渲染是否正常 (V16)"""
        self.bridge._log(">>> [UI] 触发手动信号探测 (PROBE SIGNAL)")
        # 直接在逻辑坐标 (50, 50) 画一个 200x150 的红框
        self.overlay.draw_feedback(50, 50, 200, 150)

    def on_visual_feedback_normalized(self, x, y, w, h, v_type=0):
        """物理坐标 -> 逻辑坐标转换代理 (V15/V19)"""
        scale = self.dpi_scale
        lx, ly = int(x / scale), int(y / scale)
        lw, lh = int(w / scale), int(h / scale)
        # 转发信号给 UI 线程 Slot
        self.signal_bridge.box_signal.emit(lx, ly, lw, lh, v_type)
        
    def sync_all(self):
        try:
            # 修正接口调用：从 find_target 改为 get_window_rect
            data = self.wm.get_window_rect()
            if data:
                self.overlay.is_docked = True
                self.overlay.detected_title = data["title"]
                
                # --- DPI 缩放补偿核心补丁 (V15) ---
                scale = self.dpi_scale
                
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
                    # 初始高度改为 600 或 窗口高度的 80%，避免太长
                    init_h = min(h, 750)
                    self.panel.setGeometry(px, y, self.panel.panel_width, init_h)
                    self.view_follow_h = init_h # 记录基准高度
                    self.panel_initial_docked = True
                    print(f"[HUD] 首次对位完成，高度已设为限制模式。当前物理坐标: {px}")
                else:
                    # 独立模式下，我们不再干涉面板的 XY 坐标，但保持高度跟随（如果用户没改过）
                    if not self.panel.user_touched:
                         self.panel.setFixedHeight(h)
                    
                    if self.panel.isHidden(): 
                        self.panel.show()
                
                # --- 核心改进：向执行引擎同步 [物理坐标] ---
                curr_physical_rect = (data["left"], data["top"], data["width"], data["height"])
                if not hasattr(self, "_last_phys_rect") or self._last_phys_rect != curr_physical_rect:
                    self.bridge.skills._save_dock_rect(data["left"], data["top"], data["width"], data["height"])
                    self._last_phys_rect = curr_physical_rect
            else:
                self.overlay.is_docked = False
                self.overlay.hide()
                # 强制重置 HWND 以便下次重新全桌扫描
                self.wm.hwnd = None 
                
                # 仅在从未就位时，才强制显示在右侧。一旦用户动过或就位过，就不再强制打断用户
                if not self.panel_initial_docked and not self.panel.user_touched:
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
