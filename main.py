# -*- coding: utf-8 -*-
import sys
import traceback
import io
import ctypes
import json
import os
import cv2
import base64
import re
import threading
import queue
import time
import random
import win32api
import win32con
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QMouseEvent

# ---------------------------------------------------------
# V6.6 标准化架构：Tina 视觉对位引擎
# 遵循 standardization_plan.md 规范
# ---------------------------------------------------------

# 强制设置控制台输出为 UTF-8
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 核心架构导入
from src.drivers.window import WindowManager
from src.core.viewport import ViewportManager
from src.vision.capture import VisionCapture
from src.vision.ocr_reader import OCRReader
from src.vision.layout_parser import LayoutParser
from src.ai.cloud_engine import DoubaoAIEngine
from src.ui.overlay.overlay_window import OverlayWindow
from src.ui.overlay.ui_panels import TaskPanel, LogPanel, ControlBar

class DraggableContainer(QWidget):
    """可自由拖拽的 UI 容器"""
    def __init__(self):
        super().__init__()
        self.dragging = False
        self.drag_position = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = False

class AIAgentApp:
    def __init__(self):
        print("--- Agent Standardization Boot (V6.6) ---")
        
        # [V7.20] 核心解耦水箱
        self.msg_queue = queue.Queue()
        
        # 1. 基础驱动初始化
        self.viewport_manager = ViewportManager()
        kw = self.viewport_manager.config.get("window_keyword", "Tina")
        self.window_manager = WindowManager(keywords=[kw, "MSI", "Chrome", "Response", "Google Chrome"])
        self.viewport_manager = ViewportManager()
        self.vision_capture = VisionCapture()
        
        # [V7.20] 启动 UI 哨兵定时器 (100ms 刷新一次)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._poll_messages)
        self.ui_timer.start(100)
        
        # [V7.0] 核心枢纽：初始化 TaskBridge 并实现资源共享
        from src.core.bridge import TaskBridge
        self.bridge = TaskBridge()
        self.bridge.skills.wm = self.window_manager
        self.bridge.skills.vc = self.vision_capture
        # [V7.09] 简化注册：直接信任 MSISkills 自带的动态装配
        # MSISkills 内部已经自动绑定了 atomic_skills 里的所有函数
        
        # [V7.01] 转发日志
        self.bridge._log = lambda msg: self.log("BRIDGE", msg)
        self.ai_engine = DoubaoAIEngine()
        self.ai_queue = [] # 视觉分析队列 (V6.6)
        
        # 2. UI 组件初始化
        self.overlay = OverlayWindow()
        self.task_panel = TaskPanel()
        self.log_panel = LogPanel()
        self.control_bar = ControlBar()
        self._stop_requested = False
        
        # 3. UI 布局组装
        self._setup_ui()
        
        # 4. 信号绑定
        self.task_panel.task_selected.connect(self.initiate_task)
        self.control_bar.stop_clicked.connect(self._request_stop)
        self.control_bar.quit_clicked.connect(QApplication.quit)
        
        # 5. 开启实时同步计时器 (V6.8 强力吸附)
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._periodic_sync)
        self.sync_timer.start(1000) # 每秒同步一次
        
        # 6. 自动测试钩子
        QTimer.singleShot(1500, lambda: self.initiate_task("【核心】窗口物理锁定与吸附对齐"))

    def _setup_ui(self):
        """组装侧边控制面板"""
        self.side_container = DraggableContainer()
        self.side_container.setWindowTitle("Antigravity_Control_Panel")
        self.side_container.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.side_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self.side_container)
        layout.setSpacing(15) # 面板之间的间距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.task_panel)
        layout.addWidget(self.log_panel)
        layout.addWidget(self.control_bar)
        
        # 默认位置：屏幕左侧
        self.side_container.setGeometry(20, 50, 320, 900)
        self.side_container.show()
        self.overlay.show()

    def log(self, category, msg):
        """统一日志分发 (队列解耦版)"""
        timestamp = time.strftime("%H:%M:%S")
        # 直接打印到控制台，确保可见
        print(f"[{timestamp}] [{category}] {msg}")
        
        # 写入队列，由 UI 定时器取出
        if hasattr(self, 'msg_queue'):
            self.msg_queue.put((category, msg))

    def _poll_messages(self):
        """[V7.20] UI 哨兵：定时从队列中提取日志和状态更新"""
        if not hasattr(self, 'msg_queue'): return
        
        # 处理待处理的消息
        processed = 0
        while not self.msg_queue.empty() and processed < 10:
            try:
                cat, msg = self.msg_queue.get_nowait()
                self.log_panel.append_log(cat, msg)
                processed += 1
            except: break
            
        if processed > 0:
            # [V7.22] 移除手动滚动逻辑，防止属性错误。LogPanel 内部会自动处理。
            pass
            
        # 顺便更新 HUD 状态
        self._update_bridge_status()

    # =========================================================
    # 任务分发中心 (Orchestrator)
    # =========================================================

    def initiate_task(self, task_name):
        # [V6.98] 控制台先行，确保即使 UI 卡死也能看到日志
        print(f"\n[ORCHESTRATOR] 接收到任务请求: {task_name}")
        self.log("SYSTEM", f"触发任务: {task_name}")
        self._stop_requested = False 
        
        # 模糊匹配逻辑
        tn = task_name.lower()
        if "锁定" in tn or "吸附" in tn:
            self._handle_window_lock()
        elif "双窗" in tn or "全自动" in tn:
            # [V7.10] 修正：加载昨天验证成功的 V4 拟人化版本
            flow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "panels", "tina_marking_v4_humanoid.json")
            if not os.path.exists(flow_path):
                # 如果找不到 V4，回退到普通版本
                flow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "panels", "ai_flow.json")
            
            self.log("SYSTEM", f"正在加载任务蓝图: {os.path.basename(flow_path)}")
            self.bridge.load_mission(custom_path=flow_path)
            
            # [V7.11] 强制线程启动监控
            def _async_start():
                print(">>> [THREAD_DEBUG] 线程内部开始运行")
                try:
                    if not self.bridge.steps:
                        self.log("ERROR", "错误：任务步骤列表为空，无法启动。")
                        return
                        
                    self.log("SYSTEM", ">>> 启动物理唤醒序列...")
                    self._skill_force_activate()
                    
                    self.log("SYSTEM", ">>> 移交指挥权给昨日‘冠军引擎’...")
                    self.bridge.run_mission(callback=lambda: QTimer.singleShot(0, self._update_bridge_status))
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    self.log("ERROR", f"后台线程崩溃: {str(e)}")
                    print(f"!!! [THREAD_CRASH]\n{error_detail}")
            
            self.log("DEBUG", "正在创建后台任务线程...")
            t = threading.Thread(target=_async_start, daemon=True)
            t.start()
            print(f">>> [THREAD_DEBUG] 线程已启动: {t.name}")
        elif "比武" in tn or "诊断" in tn:
            threading.Thread(target=self._run_triple_engine_test, daemon=True).start()
        elif "图标" in tn or "豆包" in tn:
            threading.Thread(target=self._run_ai_icon_recognition, daemon=True).start()
        elif "ocr" in tn or "对位" in tn or "定位" in tn:
            # [V12.1] OCR 专项测试分发
            if "多行" in tn:
                flow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "panels", "test_multi_row.json")
            elif "行对位" in tn:
                flow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "panels", "test_ocr_click.json")
            else:
                flow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "panels", "test_landmark_click.json")
            self.log("SYSTEM", f"正在加载 OCR 专项测试: {os.path.basename(flow_path)}")
            self.bridge.load_mission(custom_path=flow_path)
            
            def _async_test_start():
                self.log("SYSTEM", ">>> 启动视觉对位测试序列...")
                self._skill_force_activate()
                self.bridge.run_mission(callback=lambda: QTimer.singleShot(0, self._update_bridge_status))
                
            threading.Thread(target=_async_test_start, daemon=True).start()
        else:
            print(f"[WARNING] 未知任务名: {task_name}")
            self.log("WARNING", "该任务逻辑尚未标准化。")

    def _update_bridge_status(self):
        """[V7.15] 将 Bridge 的步骤状态实时反馈到 HUD 仪表盘"""
        if not hasattr(self, 'bridge') or not self.bridge.steps:
            return
            
        current_step = next((s for s in self.bridge.steps if s.status == "running"), None)
        
        if current_step:
            msg = f"RUNNING | {current_step.name}"
            # 同时也更新日志面板，确保醒目
            print(f">>> UI 同步进度: {msg}")
        else:
            # 任务结束或空闲
            rect = self.window_manager.get_window_rect()
            if rect:
                w = rect.get('width', 0)
                h = rect.get('height', 0)
                msg = f"HUD V6.6 | 准备就绪 {w}x{h}"
            else:
                msg = "HUD V6.6 | 等待窗口锁定..."
            
        # 安全更新 UI
        try:
            self.overlay.status_msg = msg
            QApplication.processEvents() # 强制刷新
        except: pass

    def _request_stop(self):
        """发起停止请求"""
        self._stop_requested = True
        self.log("WARNING", "正在请求终止当前工作流...")

    # =========================================================
    # 核心驱动方法 (遵循 standardization_plan.md)
    # =========================================================

    def _handle_window_lock(self):
        """[V6.0 规范] 物理对位：暴力吸附并移除边框"""
        vpm = self.viewport_manager
        u_scale = vpm.user_scale
        
        self.log("EXEC", f"正在执行强力锁定 (标准化 V6.0, 倍率: {u_scale}x)...")
        
        # 1. 寻找目标窗口并锁定物理尺寸
        target_w_phys, target_h_phys = vpm.get_physical_dims()
        success = self.window_manager.lock_window_to_size(target_w_phys, target_h_phys)
        
        if success:
            rect = self.window_manager.get_window_rect()
            self.log("SUCCESS", f"窗口已物理锁定: ({rect['left']}, {rect['top']})")
        else:
            # [V7.40] 强力兜底：如果锁定失败，尝试直接抓取当前活跃窗口坐标
            rect = self.window_manager.get_window_rect()
            if rect:
                self.log("WARNING", f"暴力锁定未完全成功，但已强行抓取到坐标: ({rect['left']}, {rect['top']})")
            else:
                self.log("ERROR", "未找到匹配窗口，请确认远程窗口已打开且标题包含 Tina/MSI/Chrome。")
                return

        # --- 统一同步路径 ---
        if rect:
            # [V7.39] 同步视口数据到技能引擎
            if hasattr(self.bridge.skills, 'vm'):
                self.bridge.skills.vm.update_dock_rect({
                    "x": rect['left'], "y": rect['top'], 
                    "width": rect['width'], "height": rect['height']
                })
            
            # [V6.95] 线程安全计算与 UI 更新
            screen = QApplication.primaryScreen()
            dpi_scale = screen.devicePixelRatio()
            
            lx = int(rect['left'] / dpi_scale)
            ly = int(rect['top'] / dpi_scale)
            lw = int(rect['width'] / dpi_scale)
            lh = int(rect['height'] / dpi_scale)
            
            status_text = f"HUD V6.6 | SCALE: {vpm.user_scale}x | {rect['width']}x{rect['height']}"
            
            # 统一在主线程更新 UI
            QTimer.singleShot(0, lambda: self._sync_ui_safe(lx, ly, lw, lh, status_text))
            
            # [V6.76] 强力激活焦点
            hwnd = self.window_manager.hwnd
            if hwnd:
                win32api.PostMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                try:
                    import ctypes
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                except:
                    pass

    def _sync_ui_safe(self, x, y, w, h, status):
        """主线程安全更新 HUD"""
        self.overlay.update_geometry({'left': x, 'top': y, 'width': w, 'height': h})
        self.overlay.status_msg = status

    def _periodic_sync(self):
        """[V6.8] 核心对位补丁：实时同步 HUD 到物理窗口"""
        rect = self.window_manager.get_window_rect()
        if rect:
            vpm = self.viewport_manager
            # 获取当前屏幕缩放比例
            screen = QApplication.primaryScreen()
            dpi_scale = screen.devicePixelRatio()
            
            # 换算逻辑坐标
            lx = int(rect['left'] / dpi_scale)
            ly = int(rect['top'] / dpi_scale)
            lw = int(rect['width'] / dpi_scale)
            lh = int(rect['height'] / dpi_scale)
            
            # 只有在位置发生明显变化时才更新，防止抖动
            if abs(self.overlay.x() - lx) > 2 or abs(self.overlay.y() - ly) > 2:
                self.overlay.update_geometry({'left': lx, 'top': ly, 'width': lw, 'height': lh})
                self.overlay.status_msg = f"LIVE SYNC | {rect['width']}x{rect['height']}"

    def _run_triple_engine_test(self):
        """[V6.6] 三引擎精度比武 (OCR + Layout + AI)"""
        self.log("SYSTEM", "正在启动三引擎联合比武...")
        
        # 1. 获取物理快照
        rect = self.window_manager.get_window_rect()
        if not rect: return
        
        self.overlay.hide()
        time.sleep(0.1)
        img = self.vision.capture_region_np(rect)
        self.overlay.show()
        
        if img is None: return

        # 2. 并行执行基础识别 (OCR + Layout)
        ocr = OCRReader()
        layout = LayoutParser()
        
        ocr_res = ocr.get_detailed_results(img)
        layout_res = layout.detect_blocks(img)
        
        # 3. 计算动态校准比例 (核心对位算法)
        ratio = self.viewport_manager.get_actual_ratio(self.overlay.width())
        self.log("DEBUG", f"动态校准比例: {ratio:.2f}")

        ar_elements = []
        # OCR (绿框)
        for (bbox, text, _) in ocr_res:
            x, y = int(bbox[0][0]/ratio), int(bbox[0][1]/ratio)
            w, h = int((bbox[2][0]-bbox[0][0])/ratio), int((bbox[2][1]-bbox[0][1])/ratio)
            ar_elements.append({'type': 'box', 'rect': [x, y, w, h], 'color': QColor(0, 255, 187), 'label': text})
        
        # Layout (黄框)
        for block in layout_res:
            bx, by, bw, bh = block["rect"]
            ar_elements.append({'type': 'box', 'rect': [int(bx/ratio), int(by/ratio), int(bw/ratio), int(bh/ratio)], 'color': QColor(255, 200, 0)})

        # 统一在主线程绘制
        QTimer.singleShot(0, lambda: self.overlay.update_ar_elements(ar_elements))
        self.log("SYSTEM", f"基础比武结束: OCR({len(ocr_res)}) | Layout({len(layout_res)})")

    def _run_ai_icon_recognition(self):
        """[V6.6] AI 深度实时分析"""
        self.log("EXEC", "正在调用 AI 进行深度视觉对位...")
        
        rect = self.window_manager.get_window_rect()
        if not rect: return
        
        self.overlay.hide()
        time.sleep(0.1)
        img = self.vision.capture_region_np(rect)
        self.overlay.show()
        
        if img is None: return

        # 图像预处理
        h, w = img.shape[:2]
        target_w = 800
        img_small = cv2.resize(img, (target_w, int(h * (target_w/w))))
        _, buffer = cv2.imencode('.jpg', img_small, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        img_b64 = base64.b64encode(buffer).decode('utf-8')

        prompt = """
        请识别图片中的所有可点击图标。返回格式为 JSON 数组：
        [{"name": "图标名", "center_x": 0-1000, "center_y": 0-1000, "w": 0-1000, "h": 0-1000}]
        """
        
        response_text = self.ai_engine.inference(prompt, img_b64)
        
        try:
            import re
            match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if match:
                icons = json.loads(match.group())
                ratio = self.viewport_manager.get_actual_ratio(self.overlay.width())
                
                ar_elements = []
                for icon in icons:
                    cx = icon.get('center_x', icon.get('x', 500))
                    cy = icon.get('center_y', icon.get('y', 500))
                    wn = icon.get('w', 40)
                    hn = icon.get('h', 40)
                    
                    # 物理中心
                    cx_phys = (cx / 1000.0) * rect['width']
                    cy_phys = (cy / 1000.0) * rect['height']
                    
                    # 逻辑尺寸
                    lw = int((wn / 1000.0 * rect['width']) / ratio)
                    lh = int((hn / 1000.0 * rect['height']) / ratio)
                    
                    # 逻辑左上角
                    lx = int(cx_phys / ratio - lw/2)
                    ly = int(cy_phys / ratio - lh/2)
                    
                    ar_elements.append({'type': 'box', 'rect': [lx, ly, lw, lh], 'color': QColor(255, 50, 50), 'label': icon['name']})
                
                # 统一在主线程绘制
                QTimer.singleShot(0, lambda: self.overlay.update_ar_elements(ar_elements))
                self.log("SUCCESS", f"AI 识别成功，发现 {len(icons)} 个图标。")
        except Exception as e:
            self.log("ERROR", f"AI 渲染失败: {str(e)}")

    def _run_complex_workflow(self):
        """[V6.6] 积木化任务流执行器：解析 ai_flow.json"""
        print("\n>>> [THREAD_START] 进入工作流线程")
        flow_path = r"D:\Dev\autoplay\config\panels\ai_flow.json"
        
        if not os.path.exists(flow_path):
            self.log("ERROR", f"找不到配置文件: {flow_path}")
            return
            
        try:
            print(f">>> 正在读取 JSON: {flow_path}")
            with open(flow_path, "r", encoding="utf-8") as f:
                content = f.read()
                flow = json.loads(content)
            
            flow_name = flow.get("name", "未命名工作流")
            print(f">>> JSON 解析成功: {flow_name}")
            self.log("SYSTEM", f"开始执行流水线: {flow_name}")
            
            steps = flow.get("steps", [])
            self.ai_queue = [] # 每次启动前清空队列
            
            # [V6.9] 启动前强制激活远程窗口
            self._skill_force_activate()
            
            for step in steps:
                if self._stop_requested:
                    self.log("WARNING", "任务已被用户手动终止。")
                    break
                    
                skill = step.get("skill")
                params = step.get("params", {})
                step_name = f"步骤 {step['id']}: {step['name']}"
                
                print(f">>> 正在执行: {step_name} | 技能: {skill}")
                self.log("EXEC", step_name)
                
                # 同步到 HUD
                status_txt = f"RUNNING | {step_name}"
                QTimer.singleShot(0, lambda: setattr(self.overlay, 'status_msg', status_txt))
                
                # --- 原子技能分发 ---
                if skill == "lock_window_position":
                    self._handle_window_lock()
                elif skill == "human_idle_move":
                    self._skill_idle_move(params.get("duration", 2))
                elif skill == "ai_clear":
                    self.ai_queue = []
                elif skill == "scroll_up":
                    self._skill_scroll(params.get("times", 1), direction="up")
                elif skill == "scroll_down":
                    self._skill_scroll(params.get("times", 1), direction="down")
                elif skill == "ai_snap":
                    self._skill_ai_snap()
                elif skill == "ai_analyze":
                    self._skill_ai_analyze(params.get("prompt", ""))
                
                time.sleep(1.0) # 步间停顿
            
            self.log("SUCCESS", f"流水线 {flow['name']} 已顺利跑通！")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"\n!!! [WORKFLOW_CRASH] 流水线执行严重错误:\n{error_details}")
            self.log("ERROR", f"工作流崩溃: {str(e)}")

    # =========================================================
    # 原子技能实现 (Atomic Skills)
    # =========================================================

    def _skill_force_activate(self):
        """[V6.9] 物理唤醒：将鼠标移至中心并执行激活点击"""
        rect = self.window_manager.get_window_rect()
        if rect:
            cx = rect['left'] + rect['width'] // 2
            cy = rect['top'] + rect['height'] // 2
            self.log("DEBUG", f"正在尝试激活窗口，目标坐标: ({cx}, {cy})")
            
            # 物理移动与点击
            win32api.SetCursorPos((cx, cy))
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.5)

    def _skill_idle_move(self, duration):
        """模拟人类闲置晃动鼠标"""
        end_time = time.time() + duration
        while time.time() < end_time:
            dx, dy = random.randint(-20, 20), random.randint(-20, 20)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)
            time.sleep(0.1)

    def _skill_scroll(self, times, direction="down"):
        """模拟滚轮滚动 (增加焦点锁定)"""
        rect = self.window_manager.get_window_rect()
        if rect:
            # 1. 确保鼠标在窗口中心，否则滚动可能发往其他地方
            cx = rect['left'] + rect['width'] // 2
            cy = rect['top'] + rect['height'] // 2
            win32api.SetCursorPos((cx, cy))
            
        amount = -400 if direction == "down" else 400
        for _ in range(times):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            time.sleep(0.3)

    def _skill_ai_snap(self):
        """抓取当前窗口并存入待分析队列"""
        rect = self.window_manager.get_window_rect()
        if not rect or 'left' not in rect: 
            self.log("ERROR", "抓图失败：未锁定窗口。")
            return
            
        self.overlay.hide()
        QApplication.processEvents() # 强制 UI 刷新
        time.sleep(0.3)
        # [V7.08] 修复变量名引用
        img = self.vision_capture.capture_region_np(rect)
        self.overlay.show()
        
        if img is not None:
            # 压缩图像
            img_small = cv2.resize(img, (800, int(img.shape[0] * (800/img.shape[1]))))
            _, buffer = cv2.imencode('.jpg', img_small, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            self.ai_queue.append(img_b64)
            self.log("SUCCESS", f"快照已入库，当前队列: {len(self.ai_queue)}")

    def _skill_ai_analyze(self, prompt):
        """调用大模型进行多图综合研判"""
        if not self.ai_queue:
            self.log("WARNING", "AI 队列为空，无法分析。")
            return
        self.log("EXEC", "正在投喂多张快照给豆包进行研判...")
        res = self.ai_engine.inference(prompt, self.ai_queue)
        
        # 显示在审批弹窗中
        from src.ui.overlay.ui_panels import ApprovalDialog
        if not hasattr(self, 'approval_dialog'):
            self.approval_dialog = ApprovalDialog()
        self.approval_dialog.show_workflow(res)
        self.log("SUCCESS", "AI 分析完成，请在弹出窗口查阅详情。")

    def _skill_force_activate(self):
        """[V7.07] 强制对齐并激活远程窗口"""
        rect = self.window_manager.get_window_rect()
        if not rect or 'left' not in rect: return
        
        cx = rect['left'] + rect['width'] // 2
        cy = rect['top'] + rect['height'] // 2
        self.log("DEBUG", f"正在物理对位并点击激活 ({cx}, {cy})...")
        
        win32api.SetCursorPos((cx, cy))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    agent = AIAgentApp()
    sys.exit(app.exec())
