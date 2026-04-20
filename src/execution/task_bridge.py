import sys
import threading
import json
import os
from typing import Callable, List, Dict

sys.path.append(r"D:/Dev/autoplay")
from src.tasks.msi_skills import MSISkills

class TaskStep:
    def __init__(self, name: str, methodName: str, params: dict, description: str):
        self.name = name
        self.methodName = methodName
        self.params = params
        self.description = description
        self.status = "idle" # idle, running, success, failed

class TaskBridge:
    """
    V14 积木化任务驱动引擎：动态解析 JSON 蓝图并调度原子技能。
    """
    def __init__(self):
        self.skills = MSISkills()
        self.config_path = r"D:/Dev/autoplay/config/missions.json"
        self.steps: List[TaskStep] = []
        self.load_mission()

    def load_mission(self, mission_name: str = None):
        """从 JSON 加载积木流"""
        if not os.path.exists(self.config_path):
            return
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        target = mission_name or data.get("current_mission")
        raw_steps = data.get("missions", {}).get(target, [])
        
        self.steps = [
            TaskStep(s["name"], s["action"], s.get("params", {}), s.get("description", ""))
            for s in raw_steps
        ]
        print(f"[BRIDGE] 成功加载积木流: {target} ({len(self.steps)} 块)")

    def run_step(self, index: int, callback: Callable = None):
        """执行单块积木"""
        if index < 0 or index >= len(self.steps): return

        step = self.steps[index]
        step.status = "running"
        if callback: callback()

        def _worker():
            try:
                # 动态反射执行原子技能
                method = getattr(self.skills, step.methodName)
                result = method(**step.params)
                step.status = "success" if result is not False else "failed"
            except Exception as e:
                print(f"[BRIDGE] 积木执行异常 {step.name}: {e}")
                step.status = "failed"
            
            if callback: callback()

        threading.Thread(target=_worker, daemon=True).start()

    def reset(self):
        for s in self.steps: s.status = "idle"
