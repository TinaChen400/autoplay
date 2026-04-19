import sys
import traceback

print("--- Agent Boot Started ---")

try:
    import os
    import threading
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from PyQt6.QtCore import Qt, QTimer
    print("[OK] Base Imports")

    from src.overlay.overlay_window import OverlayWindow
    from src.overlay.ui_panels import TaskPanel, LogPanel, ApprovalDialog
    from src.utils.window_lock import WindowManager
    from src.utils.vision import VisionCapture
    from src.ai.cloud_engine import DoubaoAIEngine
    from src.ai.model_manager import AIModelManager
    from src.execution.task_machine import TaskMachine, TaskStatus
    from src.execution.py_executor import PyExecutor
    from src.monitor.logger import SystemLogger
    print("[OK] Project Imports")

    class AIAgentApp(QMainWindow):
        def __init__(self):
            super().__init__()
            print("Init: Creating Logger...")
            # 强制 D 盘绝对日志路径
            self.logger = SystemLogger(log_dir=r"D:\Dev\autoplay\logs")
            print("Init: Creating Executor...")
            self.executor = PyExecutor(self.logger)
            print("Init: Creating WindowManager...")
            self.window_manager = WindowManager(keywords=["Google Chrome", "Chrome", "远程桌面"])
            
            print("Init: Creating Engine...")
            self.ai_engine = DoubaoAIEngine()
            self.ai_manager = AIModelManager(self.ai_engine)
            self.vision = VisionCapture()
            self.task_machine = TaskMachine(self.executor, self.logger)
            
            # --- 自动测试任务 (0 Token) ---
            print("Init: Setting Auto-Test Hook...")
            QTimer.singleShot(2000, lambda: self.initiate_task("任务：网页输入 123456"))
            
            print("Init: Building UI Panels...")
            container = QWidget()
            layout = QVBoxLayout()
            self.task_panel = TaskPanel()
            self.log_panel = LogPanel()
            layout.addWidget(self.task_panel)
            layout.addWidget(self.log_panel)
            container.setLayout(layout)
            self.setCentralWidget(container)
            
            # 信号绑定
            self.task_panel.task_selected.connect(self.initiate_task)
            self.logger.log_emitted.connect(self.log_panel.append_log)
            
            self.window_rect = None
            self.logger.log("SYSTEM", "Agent 终极版已就绪。")
            print("Agent Init Complete.")

        def initiate_task(self, task_name):
            print(f"Task Triggered: {task_name}")
            if self.task_machine.status != TaskStatus.IDLE: return
            
            # 命中硬盘记忆
            cached = self.task_machine.workflow_cache.get(task_name)
            if cached:
                self.logger.log("SYSTEM", f"命中硬盘记忆: {task_name} (0 Token)")
                self.task_machine.current_workflow = cached
                self.task_machine.status = TaskStatus.EXECUTING
                self.window_rect = self.window_manager.get_chrome_rect()
                self.task_machine.execute_approved_workflow(self.window_rect)
                return

            self.task_machine.start_task_analysis(task_name)
            self.window_rect = self.window_manager.get_chrome_rect()
            threading.Thread(target=self._run_async, args=(task_name,), daemon=True).start()

        def _run_async(self, task_name):
            try:
                temp_img = self.vision.capture_screen()
                result = self.ai_manager.get_inference(task_name, "", temp_img)
                if result.get("success"):
                    self.task_machine.receive_workflow(result.get("workflow"))
                    self.task_machine.execute_approved_workflow(self.window_rect)
            except Exception as e:
                print(f"Async Error: {e}")

    if __name__ == "__main__":
        print("Main: Starting Application...")
        app = QApplication(sys.argv)
        window = AIAgentApp()
        window.show()
        print("Main: Entering Event Loop...")
        sys.exit(app.exec())

except Exception:
    print("--- FATAL BOOT ERROR ---")
    traceback.print_exc()
    sys.exit(1)
