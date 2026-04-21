import sys
import threading
import json
import os
import time
from typing import Callable, List, Dict

sys.path.append(r"D:/Dev/autoplay")
from src.tasks.msi_skills import MSISkills
from src.execution.recorder import MissionRecorder

class TaskStep:
    def __init__(self, name: str, methodName: str, params: dict, description: str):
        self.name = name
        self.methodName = methodName
        self.params = params
        self.description = description
        self.status = "idle" # idle, running, success, failed
        self.result_data = "" # 用于存放过程结果（如 AI 决策词）

class TaskBridge:
    """
    V14 积木化任务驱动引擎：动态解析 JSON 蓝图并调度原子技能。
    """
    def __init__(self):
        self.skills = MSISkills(bridge=self)
        self.config_path = r"D:/Dev/autoplay/config/missions.json"
        self.debug_log = r"D:/Dev/autoplay/records/hud_debug.log"
        self.steps: List[TaskStep] = []
        self.is_recording = False
        self.on_step_added_cb = None # UI 刷新回调
        self.on_visual_feedback_cb = None # 视觉框反馈回调 (V11)
        self._log("TaskBridge 引擎初始化完毕。")
        self.load_mission()
        self.recorder = MissionRecorder(self, self.skills.hw, self.skills)

    def _log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.debug_log, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
        print(msg)

    @property
    def all_mission_names(self) -> List[str]:
        return list(self.full_config.get("missions", {}).keys())

    def load_mission(self, mission_name: str = None):
        """从 JSON 加载积木流"""
        if not os.path.exists(self.config_path): return
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.full_config = json.load(f)
            
        self.current_mission_name = mission_name or self.full_config.get("current_mission", "图片打分任务")
        mission_data = self.full_config.get("missions", {}).get(self.current_mission_name, [])
        
        # 兼容性补丁：检查是直接的步骤列表，还是包含元数据的对象
        if isinstance(mission_data, dict):
            raw_steps = mission_data.get("steps", [])
        else:
            raw_steps = mission_data
            
        self.steps = [
            TaskStep(s["name"], s["action"], s.get("params", {}), s.get("description", ""))
            for s in raw_steps
        ]
        print(f"[BRIDGE] 加载任务: {self.current_mission_name} ({len(self.steps)} 步)")

    def save_mission(self):
        """将当前内存中的积木流持久化回 JSON (结构化升级版)"""
        if not hasattr(self, 'full_config'): return
        serialized_steps = [
            {"name": s.name, "action": s.methodName, "params": s.params, "description": s.description}
            for s in self.steps
        ]
        
        # 智能写入：如果是字典结构，更新其中的 steps；如果是列表结构，直接替换
        current_data = self.full_config["missions"].get(self.current_mission_name)
        if isinstance(current_data, dict):
            current_data["steps"] = serialized_steps
        else:
            self.full_config["missions"][self.current_mission_name] = serialized_steps
            
        self.full_config["current_mission"] = self.current_mission_name
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.full_config, f, indent=2, ensure_ascii=False)
        print(f"[BRIDGE] 配置已成功保存(结构敏感型): {self.current_mission_name}")

    def run_step(self, index: int, callback: Callable = None):
        """执行单块积木 (加固版：防冲突 + 实时反馈)"""
        if index < 0 or index >= len(self.steps): return
        step = self.steps[index]
        
        # 状态保护：如果该积木正在跑，拒绝重复启动
        if step.status == "running": 
            self._log(f"[BRIDGE] 警告: 积木 {step.name} 尚未结束，忽略请求。")
            return
            
        step.status = "running"
        self._log(f"[BRIDGE] >>> 手动启动单步: {step.name}")
        if callback: callback()

        def _worker():
            try:
                self._log(f"[THREAD] 正在进入技能核心: {step.methodName}")
                method = getattr(self.skills, step.methodName)
                result = method(**step.params)
                step.status = "success" if result is not False else "failed"
                self._log(f"[THREAD] 积木执行完成! 结果={step.status}")
            except Exception as e:
                import traceback
                error_msg = traceback.format_exc()
                self._log(f"[THREAD] 崩溃异常:\n{error_msg}")
                step.status = "failed"
            finally:
                if callback: callback()
                # 显式补丁：触发 UI 通告
                if self.on_step_added_cb: self.on_step_added_cb()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t

    def run_mission(self, callback: Callable = None):
        """全自动驾驶：按顺序跑完所有积木"""
        print("[MISSION] 准备启动全自动指挥流程...")
        self.reset()
        def _chain_executor():
            print("[MISSION] _chain_executor 后台线程已激活！")
            for i in range(len(self.steps)):
                step = self.steps[i]
                print(f"[MISSION] 正在自动执行第 {i+1} 步: {step.name}")
                
                # 阻塞式执行（在工作线程中）
                try:
                    step.status = "running"
                    if callback: callback()
                    
                    print(f"[MISSION] 正在反射调用积木函数: {step.methodName}...")
                    method = getattr(self.skills, step.methodName)
                    result = method(**step.params)
                    print(f"[MISSION] 积木函数 {step.methodName} 返回结果: {result}")
                    
                    if result is False:
                        step.status = "failed"
                        print(f"[MISSION] 任务在第 {i+1} 步中断，原因：执行失败")
                        if callback: callback()
                        # 强制最后刷新一次，确保按钮恢复
                        self.reset_from_fail = True
                        break
                    
                    step.status = "success"
                    if callback: callback()
                    time.sleep(1.0) # 步骤间停顿，给系统喘息时间
                except Exception as e:
                    step.status = "failed"
                    print(f"[MISSION] 异常中断: {e}")
                    if callback: callback()
                    break
            print("[MISSION] 全自动任务流程运行结束")

        import time
        threading.Thread(target=_chain_executor, daemon=True).start()

    def delete_step(self, index: int):
        if 0 <= index < len(self.steps):
            del self.steps[index]
            self.save_mission()

    def move_step(self, index: int, direction: int):
        # direction: -1 (up), 1 (down)
        new_idx = index + direction
        if 0 <= new_idx < len(self.steps):
            self.steps[index], self.steps[new_idx] = self.steps[new_idx], self.steps[index]
            self.save_mission()

    def update_step_params(self, index: int, new_params: dict):
        if 0 <= index < len(self.steps):
            self.steps[index].params.update(new_params)
            self.save_mission()

    def reset(self):
        for s in self.steps: s.status = "idle"

    # --- 录制与管理核心 (V6 新增) ---
    def start_recording(self, mission_name=None):
        """开启录制模式"""
        if mission_name:
            self.create_new_mission(mission_name)
        self.is_recording = True
        self.recorder.start()
        self._log(f"[REC] 录制模式已激活: {self.current_mission_name}")

    def stop_recording(self):
        """停止录制并持久化"""
        self.is_recording = False
        self.recorder.stop()
        self.save_mission()
        self._log(f"[REC] 录制已停止，配置已同步至磁盘。")

    def add_recorded_step(self, step_dict):
        """由 Recorder 实时调用的回调，动态注入积木"""
        step = TaskStep(
            step_dict["name"], 
            step_dict["action"], 
            step_dict.get("params", {}), 
            step_dict.get("description", "")
        )
        self.steps.append(step)
        # 实时持久化一次，防止崩溃丢失
        self.save_mission()
        if self.on_step_added_cb:
            self.on_step_added_cb()

    def create_new_mission(self, name):
        """创建一个全新的空白任务蓝图"""
        self.current_mission_name = name
        self.steps = []
        if "missions" not in self.full_config:
            self.full_config["missions"] = {}
        
        if name not in self.full_config["missions"]:
             self.full_config["missions"][name] = []
        
        self.full_config["current_mission"] = name
        self.save_mission()
        self._log(f"[BRIDGE] 新任务已创建: {name}")

    def rename_mission(self, new_name):
        """修改当前任务的标题"""
        old_name = self.current_mission_name
        if old_name == new_name: return
        
        if old_name in self.full_config["missions"]:
            data = self.full_config["missions"].pop(old_name)
            self.full_config["missions"][new_name] = data
            self.current_mission_name = new_name
            self.save_mission()
            self._log(f"[BRIDGE] 任务重命名: {old_name} -> {new_name}")
