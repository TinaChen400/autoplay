import sys
import os
import time
import random

# Add project root to path
sys.path.append(r"D:/Dev/autoplay")

from src.vision.capture import VisionCapture
from src.drivers.window import WindowManager
from src.drivers.hardware import HardwareManager
from src.ai.oracle import GPTOracle
from src.vision.recognition_expert import RecognitionExpert

# Import Mixins
from src.skills.implementations.input_skills import InputSkillsMixin
from src.skills.implementations.visual_skills import VisualSkillsMixin
from src.skills.implementations.ai_skills import AISkillsMixin
from src.skills.implementations.text_skills import TextSkillsMixin
from src.skills.registry import registry

# [V7.10] 核心补丁：必须强制导入所有模块以激活 @skill_handler 注册表
import src.skills.implementations.atomic_skills 
import src.skills.implementations.input_skills
import src.skills.implementations.humanoid_skills
import src.skills.implementations.text_skills
import src.skills.implementations.ai_skills

class MSISkills(InputSkillsMixin, VisualSkillsMixin, AISkillsMixin, TextSkillsMixin):
    """
    V5.2 智能组装引擎 (Auto-Assembled)
    自动从 SkillRegistry 中吸取所有原子技能。
    """
    def __init__(self, bridge=None, wm=None, vc=None):
        self.bridge = bridge
        self.root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from src.core.viewport import ViewportManager
        self.wm = wm if wm else WindowManager(keywords=["Tina", "MSI", "Chrome"])
        self.vc = vc if vc else VisionCapture()
        self.vm = ViewportManager()
        
        self.oracle = GPTOracle(bridge=self.bridge)
        # [V7.96] 核心补丁：同步全局 Oracle 实例，防止 Step 17 和 Step 18 之间上下文丢失
        from src.skills.implementations.atomic_skills import get_oracle
        shared = get_oracle()
        shared.bridge = self.bridge
        
        self.expert = RecognitionExpert(vision_capture=self.vc)
        self.hw = HardwareManager()
        
        # [V7.09] 动态技能注入
        import functools
        from src.skills.humanize import random_delay
        
        self._log(f"[SKILLS] 正在装配原子技能... (总计: {len(registry.handlers)})")
        for skill_name, handler in registry.handlers.items():
            def make_skill(h):
                def skill_wrapper(*args, **kwargs):
                    random_delay() 
                    if self.wm.hwnd:
                        import win32gui
                        try:
                            if win32gui.IsIconic(self.wm.hwnd):
                                win32gui.ShowWindow(self.wm.hwnd, 9)
                            else:
                                win32gui.ShowWindow(self.wm.hwnd, 5)
                            win32gui.SetForegroundWindow(self.wm.hwnd)
                        except:
                            pass 
                    return h(self.vm, *args, **kwargs)
                return skill_wrapper
            setattr(self, skill_name, make_skill(handler))
            
        self._log(f"MSISkills V5.2 初始化完成，已加载 {len(registry.handlers)} 个原子技能。")

    def _log(self, msg):
        if self.bridge:
            self.bridge._log(f"[SKILLS] {msg}")
        else:
            print(f"[SKILLS] {msg}")

    def action_sleep(self, seconds=1.0):
        return self.sleep(seconds)

    def action_press_keys(self, keys, interval=0.5):
        return self.press_keys(keys, interval)
