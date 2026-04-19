from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QFrame, QListWidget, QListWidgetItem,
                             QTabWidget, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont

class TaskPanel(QWidget):
    """左侧任务管理面板"""
    task_selected = pyqtSignal(str) # 任务点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setMaximumHeight(800) # 限制高度，防止在竖屏下拉得太细长
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(25, 25, 25, 200); 
                color: #eee; 
                border: 2px solid rgba(0, 255, 187, 80);
                border-radius: 15px;
            }
            QLabel { border: none; background: transparent; }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("AI 任务列表")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; font-size: 15px; outline: none; }
            QListWidget::item { 
                background: rgba(255, 255, 255, 10); 
                border-radius: 8px; 
                margin-bottom: 5px; 
                padding: 10px;
            }
            QListWidget::item:hover { background: rgba(0, 255, 187, 30); }
            QListWidget::item:selected { background: rgba(0, 255, 187, 60); border: 1px solid #0fb; }
        """)
        self.task_list.itemClicked.connect(self._on_item_clicked)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.task_list)
        
        tasks = [
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
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(25, 25, 25, 200); 
                color: #eee; 
                border: 2px solid rgba(0, 255, 187, 80);
                border-radius: 15px;
            }
            QLabel { border: none; background: transparent; }
        """)
        
        layout = QVBoxLayout(self)
        
        # 资源条
        self.status_label = QLabel("状态: 空闲 (Local-AI)")
        self.status_label.setStyleSheet("color: #0fb;")
        layout.addWidget(self.status_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            background-color: rgba(0, 0, 0, 100); 
            font-family: 'Consolas', 'Courier New'; 
            color: #adff2f; 
            border: 1px solid #333;
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
