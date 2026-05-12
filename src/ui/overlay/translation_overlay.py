import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QColor, QFont

class TranslationLabel(QLabel):
    """浮动翻译标签"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setMaximumWidth(400) # 限制最大宽度，防止横向过长
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 220);
            color: #00ff7f;
            border: 2px solid #00ff7f;
            border-radius: 5px;
            padding: 6px;
            font-size: 14px;
            font-family: 'Microsoft YaHei UI';
            font-weight: bold;
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.adjustSize()

class TranslationOverlay(QWidget):
    """
    全虚空间覆盖层：支持多屏和超宽屏
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.labels = []
        
        # [V22.14] 核心修正：覆盖所有显示器区域 (虚拟桌面)
        from PyQt6.QtGui import QGuiApplication
        v_geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(v_geo)
        print(f"[AI-AR] 覆盖层已就绪，尺寸: {v_geo.width()}x{v_geo.height()}")
        
    def clear_labels(self):
        """手动清除所有翻译"""
        for label in self.labels:
            label.deleteLater()
        self.labels = []
        self.hide()

    def display_translations(self, translations: list):
        """
        translations: list of (logical_x, logical_y, w, h, text)
        """
        self.clear_labels()

        for lx, ly, w, h, text in translations:
            lbl = TranslationLabel(text, self)
            lbl.move(lx, ly)
            lbl.show()
            self.labels.append(lbl)
            print(f"[AI-RENDER] 绘制标签: '{text[:10]}...' 于逻辑位置 ({lx}, {ly})")
            
        self.show()
        # 强制置顶，防止被某些全屏窗口压在下面
        self.raise_()
