import queue
import time
import threading
import json
import os
from typing import List, Optional, Dict
from enum import Enum

class TaskStatus(Enum):
    IDLE = "空闲"
    ANALYZING = "AI 分析中"
    PENDING_APPROVAL = "待审批"
    EXECUTING = "同步执行中"
    CLEARING = "页面清空中"
    FINISHED = "已完成"
    ERROR = "异常"

class TaskMachine:
    """
    任务状态机：控制任务生命周期，与驱动执行器联动。
    支持硬盘持久化缓存，防止重复 Token 消耗。
    """
    def __init__(self, executor, logger):
        self.executor = executor
        self.logger = logger
        self.status = TaskStatus.IDLE
        self.current_workflow = None
        self.current_task_info = None
        # 强制 D 盘绝对配置路径
        self.cache_path = r"D:\Dev\autoplay\config\workflow_cache.json"
        self.workflow_cache = self._load_cache()

    def _load_cache(self) -> dict:
        """从硬盘加载历史记忆"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.log("ERROR", f"加载本地缓存失败: {e}")
        return {}

    def _save_cache(self):
        """将记忆存入硬盘"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.workflow_cache, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.logger.log("ERROR", f"保存本地缓存失败: {e}")

    def start_task_analysis(self, task_name: str):
        """进入 AI 分析阶段"""
        self.status = TaskStatus.ANALYZING
        self.current_task_info = task_name
        self.logger.log("SYSTEM", f"发起任务分析: {task_name}")

    def receive_workflow(self, workflow_text: str):
        """AI 分析完成，立刻进入执行状态，并持久化缓存"""
        self.current_workflow = workflow_text
        self.status = TaskStatus.EXECUTING
        if self.current_task_info:
            self.workflow_cache[self.current_task_info] = workflow_text
            self._save_cache() # 存入硬盘
        self.logger.log("MODEL", f"检测到新指令并已完成硬盘存档。")

    def execute_approved_workflow(self, window_rect: Optional[Dict[str, int]] = None):
        """触发执行分支"""
        if not self.current_workflow:
            return
        
        self.status = TaskStatus.EXECUTING
        threading.Thread(target=self._run_execution_thread, args=(window_rect,), daemon=True).start()

    def _run_execution_thread(self, window_rect: Optional[Dict[str, int]] = None):
        """真实的执行线程"""
        try:
            self.logger.log("EXEC", "开始执行工作流步骤...")
            import re
            
            offset_x = window_rect['left'] if window_rect else 0
            offset_y = window_rect['top'] if window_rect else 0
            
            lines = self.current_workflow.split('\n')
            for line in lines:
                # 1. 探测鼠标坐标
                nums = re.findall(r'(\d+)[,，\s]+(\d+)', line)
                # 2. 提取输入指令并剔除汉字干扰
                m = re.search(r'(?:INPUT|输入)\s*[（\(\[\[]?\s*([^）\)\]\]]+)\s*[）\)\s]?', line, re.IGNORECASE)
                
                input_content = None
                if m:
                    content = m.group(1).strip()
                    content = re.sub(r'[\u4e00-\u9fa5]+', '', content).strip() 
                    content = content.replace('(', '').replace(')', '').strip('：: ')
                    input_content = content if content else None

                if nums:
                    x, y = int(nums[0][0]), int(nums[0][1])
                    abs_x, abs_y = x + offset_x, y + offset_y
                    self.logger.log("EXEC", f"执行聚焦点击 -> ({abs_x}, {abs_y})")
                    self.executor.execute_click(abs_x, abs_y)
                    time.sleep(1.0) # 等待气门
                    # 二次点击确保激活焦点
                    self.executor.execute_click(abs_x, abs_y)
                    time.sleep(1.5) # 留出 1.5 秒确保输入框彻底准备就绪
                
                if input_content:
                    self.logger.log("EXEC", f"执行输入 -> {input_content}")
                    self.executor.execute_input(input_content)
                
                time.sleep(0.8) # 动作步进
            
            # 手尾清理
            self.status = TaskStatus.CLEARING
            self.executor.clear_page()
            
            self.status = TaskStatus.FINISHED
            self.logger.log("SYSTEM", f"任务圆满完成。")
            time.sleep(2)
            self.status = TaskStatus.IDLE
        except Exception as e:
            self.status = TaskStatus.ERROR
            self.logger.log("ERROR", f"执行过程异常: {e}")

    def get_ui_status(self) -> dict:
        return {
            "status_text": self.status.value,
            "workflow": self.current_workflow
        }
