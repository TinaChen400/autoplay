import sys
import os
import time
import random

# Add project root to path
sys.path.append(r"D:/Dev/autoplay")

from src.utils.vision import VisionCapture
from src.utils.ocr_reader import OCRReader
from src.utils.window_lock import WindowManager
from src.utils.hardware_manager import HardwareManager
from src.execution.remote_agent import RemoteAgent
from src.tasks.skill_gpt_oracle import GPTOracle
from src.utils.recognition_expert import RecognitionExpert

# Import Mixins
from src.tasks.skills.input_skills import InputSkillsMixin
from src.tasks.skills.visual_skills import VisualSkillsMixin
from src.tasks.skills.ai_skills import AISkillsMixin

class MSISkills(InputSkillsMixin, VisualSkillsMixin, AISkillsMixin):
    """
    V5.0 模块化技能引擎 (The Core Hub)
    通过继承不同的 Mixin 来组装功能，保持核心类简洁。
    """
    def __init__(self, bridge=None):
        self.bridge = bridge
        self.agent = RemoteAgent(profile_name="MSI")
        self.vc = VisionCapture()
        self.oracle = GPTOracle(bridge=self.bridge)
        self.expert = RecognitionExpert(vision_capture=self.vc)
        self.wm = WindowManager(keywords=["Tina", "MSI", "Chrome"])
        self.hw = HardwareManager()
        
        self.records_dir = r"D:/Dev/autoplay/records"
        self.db_path = r"D:/Dev/autoplay/config/calibration_db.json"
        self._log("MSISkills V5.0 (Modular Engine) initialized.")

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
