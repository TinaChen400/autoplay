import sys
import threading
from typing import Callable, List, Dict

# 加入项目根目录
sys.path.append(r"D:/Dev/autoplay")
from src.tasks.msi_skills import MSISkills

class TaskStep:
    def __init__(self, name: str, func: Callable, description: str):
        self.name = name
        self.func = func
        self.description = description
        self.status = "idle" # idle, running, success, failed

class TaskBridge:
    """
    任务桥接引擎：将 MSI 自动化脚本拆解为可单步执行的任务链。
    """
    def __init__(self):
        self.skills = MSISkills()
        self.steps: List[TaskStep] = [
            TaskStep("1. 识别并点击小图", self.skills.click_input_thumbnail, "定位 SOURCE 文字并在下方区域对位缩略图并点击"),
            TaskStep("2. 等待大图弹出", self.skills.wait_for_visual_change, "实时计算画面像素增量，检测弹窗出现"),
            TaskStep("3. 注入方向键序列", self.skills.interact_with_large_image, "穿透式注入物理按键 (下右左上)"),
        ]
        self.current_index = 0

    def run_step(self, index: int, callback: Callable = None):
        """异步执行指定步骤"""
        if index < 0 or index >= len(self.steps):
            return

        step = self.steps[index]
        step.status = "running"
        if callback: callback()

        def _worker():
            try:
                # 执行具体技能
                result = step.func()
                step.status = "success" if result is not False else "failed"
            except Exception as e:
                print(f"[BRIDGE] Error in {step.name}: {e}")
                step.status = "failed"
            
            if callback: callback()

        threading.Thread(target=_worker, daemon=True).start()

    def reset(self):
        for step in self.steps:
            step.status = "idle"
        self.current_index = 0
