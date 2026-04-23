# -*- coding: utf-8 -*-
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import logging
import ctypes
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QPen, QPainter
import win32gui
import win32api
import win32con

# 1. Kill all Qt scaling to avoid coordinate confusion
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_AUTOSCREENSCALEFACTOR"] = "0"

# 2. Try to force Per-Monitor V2 for the process
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VisualDock")

from src.utils.viewport_manager import ViewportManager
from src.utils.hardware_manager import HardwareManager

class VisualDock(QWidget):
    def __init__(self):
        super().__init__()
        self.vm = ViewportManager()
        self.hm = HardwareManager()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.is_docked = False
        self.target_hwnd = None
        self.target_title_keywords = ["tina", "remote"]
        self.current_color = QColor(0, 191, 255, 120)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(50) 
        
        self.old_pos = None
        self.resize(400, 300)
        self.physical_rect = (0, 0, 0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        border_width = 8
        painter.setPen(QPen(self.current_color, border_width))
        painter.drawRect(self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2))
        
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        info = f"Physical: {self.physical_rect[0]}, {self.physical_rect[1]} | {self.physical_rect[2]-self.physical_rect[0]}x{self.physical_rect[3]-self.physical_rect[1]}"
        if self.is_docked:
            info += "\n[STATUS: DOCKED]"
        painter.drawText(self.rect().adjusted(15, 15, -15, -15), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, info)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            if self.is_docked:
                self.is_docked = False
                self.target_hwnd = None
                self.current_color = QColor(0, 191, 255, 120)

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        # When moving manually, we don't have a target_hwnd yet
        self.physical_rect = (self.x(), self.y(), self.x() + self.width(), self.y() + self.height())
        self.sync_to_managers(self.physical_rect)

    def update_logic(self):
        if not self.is_docked:
            cx = self.x() + self.width() // 2
            cy = self.y() + self.height() // 2
            
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    if any(kw in title for kw in self.target_title_keywords):
                        rect = win32gui.GetWindowRect(hwnd)
                        if rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]:
                            extra.append(hwnd)
                            return False 
                return True

            found = []
            try: win32gui.EnumWindows(callback, found)
            except: pass
                
            if found:
                logger.info(f"SNAP! Target detected: {win32gui.GetWindowText(found[0])}")
                self.is_docked = True
                self.target_hwnd = found[0]
                self.current_color = QColor(50, 255, 50, 200)
                self.follow_win32()
        else:
            if win32gui.IsWindow(self.target_hwnd) and win32gui.IsWindowVisible(self.target_hwnd):
                self.follow_win32()
            else:
                self.is_docked = False
                self.current_color = QColor(0, 191, 255, 120)

    def follow_win32(self):
        try:
            # RAW physical coordinates from OS
            rect = win32gui.GetWindowRect(self.target_hwnd)
            self.physical_rect = rect
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            
            # Update UI geometry to match
            if (self.x(), self.y(), self.width(), self.height()) != (rect[0], rect[1], w, h):
                self.setGeometry(rect[0], rect[1], w, h)
                # Sync using the RAW rect, NOT self.x()/y()
                self.sync_to_managers(rect)
                self.update()
        except:
            self.is_docked = False

    def sync_to_managers(self, rect):
        """rect is (x1, y1, x2, y2) physical pixels."""
        data = {
            "x": rect[0],
            "y": rect[1],
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1]
        }
        self.vm.update_dock_rect(data)
        self.hm.update_calibration(data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dock = VisualDock()
    dock.show()
    sys.exit(app.exec())
