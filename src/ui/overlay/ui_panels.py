from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QFrame, QListWidget, QListWidgetItem,
                             QTabWidget, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont

class TaskPanel(QWidget):
    """左侧任务管理面板"""
    task_selected = pyqtSignal(str) # 任务点击信号
    stop_signal = pyqtSignal()      # 停止信号 (V6.7)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setMaximumHeight(800) # 限制高度，防止在竖屏下拉得太细长
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 15, 20, 240); 
                color: #e0e0e0; 
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
            }
            QLabel { border: none; background: transparent; }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("AI 任务列表")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; font-size: 15px; outline: none; color: #fff; }
            QListWidget::item { 
                background: rgba(255, 255, 255, 30); 
                border-radius: 8px; 
                margin-bottom: 5px; 
                padding: 10px;
                color: #fff;
            }
            QListWidget::item:hover { background: rgba(255, 255, 255, 20); color: #fff; }
            QListWidget::item:selected { background: rgba(255, 255, 255, 40); color: #fff; border: 1px solid rgba(255, 255, 255, 60); }
        """)
        self.task_list.itemClicked.connect(self._on_item_clicked)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.task_list)
        
        tasks = [
            {"name": "【核心】窗口物理锁定与吸附对齐", "desc": "强制固定远程窗口位置并移除边框"},
            {"name": "【高级】AI 全自动双图研判", "desc": "按 ai_flow.json 步骤执行全流程打分"},
            {"name": "【诊断】视觉引擎精度比武", "desc": "对比 OCR 与 布局分析 引擎的识别精度"},
            {"name": "【高级】豆包视觉：图标深度识别", "desc": "调用 Seed-1.8 大模型识别图片中的小图标"},
            {"name": "测试：网页自动刷新", "desc": "识别刷新图标并模拟点击"},
            {"name": "任务：检测‘确定’按钮并点击", "desc": "寻找确定/OK按钮"},
            {"name": "任务：网页输入 123456", "desc": "在搜索框输入数字并回车"}
        ]
        for t in tasks:
            self.add_task(t["name"])

    def add_task(self, name):
        item = QListWidgetItem(name)
        item.setSizeHint(QSize(0, 45))
        self.task_list.addItem(item)

    def _on_item_clicked(self, item):
        text = item.text()
        print(f"[UI_CLICK] 用户点击了任务项: {text}")
        if "网页输入" in text:
            content = text.split("网页输入 ")[-1]
            print(f"解析到 INPUT 指令: {content}")
        self.task_selected.emit(text)

class LogPanel(QWidget):
    """右侧状态监控面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        self.setMaximumHeight(800)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 15, 20, 240); 
                color: #e0e0e0; 
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
            }
            QLabel { border: none; background: transparent; }
        """)
        
        layout = QVBoxLayout(self)
        
        # 资源条
        self.status_label = QLabel("状态: 空闲 (Local-AI)")
        self.status_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self.status_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            background-color: rgba(0, 0, 0, 220); 
            font-family: 'Consolas', 'Courier New'; 
            color: #adff2f; 
            border: 1px solid #00ffbb;
            border-radius: 5px;
            padding: 5px;
        """)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.log_output)

    def update_status(self, text, color="#0fb"):
        self.status_label.setText(f"状态: {text}")
        self.status_label.setStyleSheet(f"color: {color};")

    def append_log(self, category, msg):
        timestamp = QFont("Consolas", 9)
        color = "#fff"
        if category == "EXEC": color = "#fb0"
        if category == "ERROR": color = "#f44"
        
        self.log_output.append(f"<span style='color:{color}'>[{category}] {msg}</span>")

        # 保持滚动到底部
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

class ControlBar(QWidget):
    """新增：底部控制条"""
    stop_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.btn_stop = QPushButton("紧急停止 (STOP)")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #9c2b2b; 
                color: white; 
                font-weight: bold; 
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c43535;
            }
        """)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)

        self.btn_quit = QPushButton("退出 (QUIT)")
        self.btn_quit.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2e; 
                color: #888; 
                border-radius: 8px;
                border: 1px solid #3a3a3e;
            }
            QPushButton:hover {
                background-color: #3a3a3e;
                color: #ccc;
            }
        """)
        self.btn_quit.clicked.connect(self.quit_clicked.emit)

        layout.addWidget(self.btn_stop, 2)
        layout.addWidget(self.btn_quit, 1)

class ApprovalDialog(QFrame):
    """工作流审批弹窗"""
    approved = pyqtSignal()
    rejected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(450, 350)
        # 设为独立窗口模式，确保它不会被遮挡，并保持置顶
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #1e1e1e; border: 2px solid #0fb; border-radius: 12px; color: white;")
        
        layout = QVBoxLayout(self)
        
        title = QLabel("大模型决策审批 (Ctrl+Enter)")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setStyleSheet("background-color: #000; color: #0f0; border: 1px solid #333;")
        layout.addWidget(self.content)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("审批通过")
        self.btn_ok.setStyleSheet("background-color: #2d5a27; height: 40px; border-radius: 5px;")
        self.btn_ok.clicked.connect(self.approved.emit)
        
        self.btn_no = QPushButton("驳回")
        self.btn_no.setStyleSheet("background-color: #7a2323; height: 40px; border-radius: 5px;")
        self.btn_no.clicked.connect(self.rejected.emit)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_no)
        layout.addLayout(btn_layout)
        
        self.hide()

    def show_workflow(self, workflow_text):
        self.content.setPlainText(workflow_text)
        self.show()
        # 使用 QScreen 获取全局屏幕中心，避免 Parent 坐标计算错误
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        self.raise_()
