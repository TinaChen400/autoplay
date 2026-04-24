import sys
import os
import time
import random

# Add project root to path
sys.path.append(r"D:/Dev/autoplay")

from src.vision.capture import VisionCapture
from src.vision.ocr_reader import OCRReader
from src.drivers.window import WindowManager
from src.drivers.hardware import HardwareManager
from src.ai.oracle import GPTOracle
from src.vision.recognition_expert import RecognitionExpert

# Import Mixins
from src.skills.implementations.input_skills import InputSkillsMixin
from src.skills.implementations.visual_skills import VisualSkillsMixin
from src.skills.implementations.ai_skills import AISkillsMixin
from src.skills.registry import registry
# [V7.09] 强制导入所有原子技能，激活 @skill_handler 注册表
import src.skills.implementations.atomic_skills 

class MSISkills(InputSkillsMixin, VisualSkillsMixin, AISkillsMixin):
    """
    V5.1 智能组装引擎 (Dynamic Auto-Assembled)
    自动从 SkillRegistry 中吸取所有原子技能。
    """
    def __init__(self, bridge=None, wm=None, vc=None):
        self.bridge = bridge
        self.root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 资源初始化
        from src.core.viewport import ViewportManager
        self.wm = wm if wm else WindowManager(keywords=["Tina", "MSI", "Chrome"])
        self.vc = vc if vc else VisionCapture()
        self.vm = ViewportManager() # 补充 ViewportManager 实例用于原子技能
        
        self.oracle = GPTOracle(bridge=self.bridge)
        self.expert = RecognitionExpert(vision_capture=self.vc)
        self.hw = HardwareManager()
        
        # [V7.09] 动态技能注入：将注册表中的函数绑定到实例
        import functools
        self._log(f"[SKILLS] 正在装配原子技能... (总计: {len(registry.handlers)})")
        for skill_name, handler in registry.handlers.items():
            # 将 vm 作为第一个参数注入
            setattr(self, skill_name, functools.partial(handler, self.vm))
            
        if "human_idle_move" in registry.handlers:
            self._log("[SKILLS] 关键技能 [human_idle_move] 已就绪")
        else:
            self._log("!!! [SKILLS] 警告: 找不到关键技能 human_idle_move")
            
        self.records_dir = os.path.join(self.root, "records")
        self._log("MSISkills V5.1 (Auto-Assembled) initialized.")

    def _log(self, msg):
        if self.bridge:
            self.bridge._log(f"[SKILLS] {msg}")
        else:
            print(f"[SKILLS] {msg}")

    # Legacy Compatibility
    def action_sleep(self, seconds=1.0):
        return self.sleep(seconds)

    def action_press_keys(self, keys, interval=0.5):
        return self.press_keys(keys, interval)
