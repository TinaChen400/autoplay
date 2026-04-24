import os
import json
import win32api
import time
from typing import Optional, Dict

class HardwareManager:
    """
    硬件环境感知管理器：
    负责检测当前物理环境（显示器数量、分辨率、方向）并匹配对应的对位档案。
    """
    def __init__(self):
        self.config_path = r"D:\Dev\autoplay\config\hardware_profiles.json"
        self.profiles = {}
        self.current_profile_name = "Default"
        self.load_profiles()

    def load_profiles(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", {})
                    self.current_profile_name = data.get("current_profile", "Default")
            except Exception as e:
                print(f"[HW_MANAGER] 配置文件加载失败: {e}")

    def save_profiles(self):
        data = {
            "current_profile": self.current_profile_name,
            "profiles": self.profiles
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_current_fingerprint(self) -> str:
        """
        生成当前硬件环境的数字指纹 (显示器数量_主显示器缩放_分辨率)
        """
        monitors = win32api.EnumDisplayMonitors()
        # 简单指纹：显示器数量 + 第一个显示器的尺寸
        main_monitor = monitors[0][2]
        w = main_monitor[2] - main_monitor[0]
        h = main_monitor[3] - main_monitor[1]
        return f"M{len(monitors)}_{w}x{h}"

    def auto_detect_profile(self) -> str:
        """根据硬件指纹尝试自动推回档案"""
        fingerprint = self.get_current_fingerprint()
        for name, p in self.profiles.items():
            if p.get("screen_geometry") == fingerprint.split('_')[1]:
                return name
        return self.current_profile_name

    def get_active_calibration(self) -> Dict:
        """获取当前活跃档案的校准数据"""
        p = self.profiles.get(self.current_profile_name, {})
        return p.get("calibration", {
            "dock_rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "dpi_offset_y": 140
        })

    def update_calibration(self, dock_rect: Dict, dpi_offset: int = 140):
        """实时更新当前档案的校准参数"""
        if self.current_profile_name not in self.profiles:
            fingerprint = self.get_current_fingerprint()
            self.profiles[self.current_profile_name] = {
                "device_name": "Unknown",
                "screen_geometry": fingerprint.split('_')[1],
                "calibration": {}
            }
        
        self.profiles[self.current_profile_name]["calibration"] = {
            "dock_rect": dock_rect,
            "dpi_offset_y": dpi_offset
        }
        self.profiles[self.current_profile_name]["last_updated"] = time.time()
        self.save_profiles()

    def switch_profile(self, name: str):
        if name in self.profiles:
            self.current_profile_name = name
            self.save_profiles()
            return True
        return False
