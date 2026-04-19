import sys
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

class OverlayWindow(QMainWindow):
    """
    PyQt6 透明图层控制台窗口。
    实现置顶、无边框、鼠标穿透。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Agent Overlay")
        
        # 恢复正式模式：无边框、置顶、后台采样模式
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        
        # 恢复高级感：允许透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 恢复物理层：暂时开启点击穿透，确保不干扰您的远程操作
        self.set_click_through(True)
        
        self.ar_elements = [] # 存储待绘制的视觉元素
        self.status_msg = "初始化完成"
        self._drag_pos = None

    def mousePressEvent(self, event):
        """记录点击位置用于拖拽"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """实现平滑拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def set_click_through(self, enabled: bool):
        """控制窗口是否支持鼠标穿透"""
        if enabled:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    def update_geometry(self, rect: dict):
        """
        同步远程窗口坐标。
        rect: {"left": x, "top": y, "width": w, "height": h}
        """
        self.setGeometry(rect['left'], rect['top'], rect['width'], rect['height'])

    def update_ar_elements(self, elements: list):
        """更新需要绘制的 AR 元素列表"""
        self.ar_elements = elements
        self.update() # 触发 paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景（可选，设为全透明或微弱半透明）
        # painter.fillRect(self.rect(), QColor(0, 0, 0, 1)) 

        # 遍历绘制 AR 元素
        for elem in self.ar_elements:
            self._draw_element(painter, elem)
            
        # 绘制全局状态信息
        self._draw_status(painter)

    def _draw_element(self, painter, elem):
        """绘制单个识别框或目标点"""
        etype = elem.get('type', 'box')
        color = elem.get('color', QColor(255, 0, 0)) # 默认红色
        rect = elem.get('rect', [0, 0, 0, 0])
        label = elem.get('label', '')

        painter.setPen(QPen(color, 2))
        
        if etype == 'box':
            painter.drawRect(rect[0], rect[1], rect[2], rect[3])
            if label:
                painter.setFont(QFont("Arial", 10))
                painter.drawText(rect[0], rect[1]-5, label)
        elif etype == 'point':
            painter.setBrush(color)
            painter.drawEllipse(rect[0]-3, rect[1]-3, 6, 6)

    def _draw_status(self, painter):
        """在顶部中央绘制当前系统状态（胶囊背景）"""
        margin_top = 10
        rect_w = 400
        rect_h = 30
        rect_x = (self.width() - rect_w) // 2
        
        # 绘制半透明底色
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawRoundedRect(rect_x, margin_top, rect_w, rect_h, 15, 15)
        
        # 绘制文字
        painter.setPen(QColor(0, 255, 187)) # 亮青色
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRect(rect_x, margin_top, rect_w, rect_h), Qt.AlignmentFlag.AlignCenter, f"● {self.status_msg}")

if __name__ == "__main__":
    # 简易测试代码
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    
    # 模拟更新一些绘制元素
    window.update_ar_elements([
        {'type': 'box', 'rect': [100, 100, 200, 150], 'label': 'Target Button', 'color': QColor(255, 0, 0)},
        {'type': 'point', 'rect': [400, 300], 'color': QColor(0, 0, 255)}
    ])
    
    sys.exit(app.exec())
