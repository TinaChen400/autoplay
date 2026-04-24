import sys
import threading
import json
import os
import time
from typing import Callable, List, Dict

sys.path.append(r"D:/Dev/autoplay")
from src.skills.msi_skills import MSISkills
from src.core.recorder import MissionRecorder

class TaskStep:
    def __init__(self, id: int, name: str, methodName: str, params: dict, description: str):
        self.id = id
        self.name = name
        self.methodName = methodName
        self.params = params
        self.description = description
        self.status = "idle"
class TaskBridge:
    """
    V14 积木化任务驱动引擎：动态解析 JSON 蓝图并调度原子技能。
    """
    def __init__(self):
        # [V6.99] 使用相对路径确保环境兼容性
        self.root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_path = os.path.join(self.root, "config", "missions.json")
        self.debug_log = os.path.join(self.root, "records", "hud_debug.log")
        
        self.skills = MSISkills(bridge=self)
        self.steps: List[TaskStep] = []
        self.is_recording = False
        self.on_step_added_cb = None 
        self.on_visual_feedback_cb = None 
        self._log("TaskBridge 引擎 (V14 Standard) 初始化完毕。")
        self.load_mission()

    def _log(self, msg):
        """统一日志记录：支持时间戳与文件持久化"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{timestamp}] {msg}"
            # 写入调试文件
            if hasattr(self, 'debug_log'):
                with open(self.debug_log, "a", encoding="utf-8") as f:
                    f.write(log_line + "\n")
            print(log_line)
        except Exception as e:
            print(f"[BRIDGE_LOG_ERR] {str(e)}")

    def load_mission(self, custom_path: str = None, mission_name: str = None):
        """从 JSON 加载积木流 (兼容直接步骤与任务集两种模式)"""
        target_path = custom_path if custom_path else self.config_path
        if not os.path.exists(target_path): 
            self._log(f"[BRIDGE] 错误: 找不到任务文件 {target_path}")
            return
            
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # [V7.02] 智能识别模式
        if isinstance(data, list):
            # 模式 A: 纯步骤列表
            raw_steps = data
            self.current_mission_name = os.path.basename(target_path)
        elif isinstance(data, dict) and "steps" in data:
            # 模式 B: 单个任务对象 (ai_flow.json 风格)
            raw_steps = data["steps"]
            self.current_mission_name = data.get("name", os.path.basename(target_path))
        elif isinstance(data, dict) and "missions" in data:
            # 模式 C: 任务集合 (missions.json 风格)
            self.full_config = data
            self.current_mission_name = mission_name or data.get("current_mission", "图片打分任务")
            mission_data = data.get("missions", {}).get(self.current_mission_name, [])
            raw_steps = mission_data.get("steps", []) if isinstance(mission_data, dict) else mission_data
        else:
            self._log(f"[BRIDGE] 错误: JSON 结构无法识别 {target_path}")
            return
            
        self.steps = []
        for i, s in enumerate(raw_steps):
            if not s.get("name"): continue
            step_id = s.get("id", i + 1)
            step = TaskStep(
                id=step_id,
                name=s["name"],
                methodName=s.get("action") or s.get("skill"),
                params=s.get("params", {}),
                description=s.get("description", "")
            )
            self.steps.append(step)
            
        self._log(f"[BRIDGE] 加载成功: {self.current_mission_name} ({len(self.steps)} 步)")

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
        """全自动驾驶：按顺序跑完所有积木 (V7.05 增强反馈版)"""
        self._log("[MISSION] >>> 准备启动全自动指挥流程...")
        self.reset()
        
        def _chain_executor():
            self._log("[MISSION] 后台执行引擎已就绪。")
            for i in range(len(self.steps)):
                if getattr(self, '_stop_requested', False):
                    self._log("[MISSION] 接收到终止信号，流程中断。")
                    break
                    
                step = self.steps[i]
                step_info = f"第 {i+1}/{len(self.steps)} 步: {step.name}"
                self._log(f"[MISSION] 正在执行: {step_info}")
                
                try:
                    step.status = "running"
                    if callback: callback()
                    
                    # [V7.05] 反射调用
                    if not hasattr(self.skills, step.methodName):
                        self._log(f"[MISSION] 错误: 找不到技能函数 {step.methodName}")
                        step.status = "failed"
                        if callback: callback()
                        break
                        
                    method = getattr(self.skills, step.methodName)
                    # 尝试调用并捕获结果
                    result = method(**step.params)
                    
                    if result is False:
                        self._log(f"[MISSION] 步骤执行返回失败。流程中断。")
                        step.status = "failed"
                        if callback: callback()
                        break
                    
                    step.status = "success"
                    self._log(f"[MISSION] 完成: {step.name}")
                    if callback: callback()
                    time.sleep(1.2) # 步骤间自然停顿
                except Exception as e:
                    import traceback
                    self._log(f"[MISSION] 崩溃详情: {traceback.format_exc()}")
                    step.status = "failed"
                    if callback: callback()
                    break
            self._log("[MISSION] <<< 全自动任务流程执行完毕。")

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
