# -*- coding: utf-8 -*-
"""
HardwareManager: Detects physical environment and matches hardware profiles.
"""

import os
import json
import logging
import time
import win32api
from typing import Optional, Dict

# Set up logging
logger = logging.getLogger("HardwareManager")
logger.setLevel(logging.INFO)

class HardwareManager:
    """
    HardwareManager handles environment detection (monitor setup, resolution)
    and maps it to specific calibration profiles.
    """
    
    def __init__(self, config_path: str = None):
        # Default config path relative to project root
        if config_path is None:
            self.config_path = os.path.join(os.getcwd(), 'config', 'hardware_profiles.json')
        else:
            self.config_path = config_path
            
        self.profiles = {}
        self.current_profile_name = "Default"
        self.load_profiles()

    def load_profiles(self) -> None:
        """Loads hardware profiles from JSON."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Hardware profiles not found at {self.config_path}. Using defaults.")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.profiles = data.get("profiles", {})
                self.current_profile_name = data.get("current_profile", "Default")
            logger.info(f"Loaded hardware profiles. Active: {self.current_profile_name}")
        except Exception as e:
            logger.error(f"Failed to load hardware profiles: {e}")

    def save_profiles(self) -> None:
        """Saves current profiles to JSON."""
        try:
            data = {
                "current_profile": self.current_profile_name,
                "profiles": self.profiles
            }
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info("Hardware profiles saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save hardware profiles: {e}")

    def get_current_fingerprint(self) -> str:
        """Generates a fingerprint of the current monitor setup."""
        try:
            monitors = win32api.EnumDisplayMonitors()
            # Basic fingerprint: Monitor count + Main monitor resolution
            main_monitor = monitors[0][2]
            w = main_monitor[2] - main_monitor[0]
            h = main_monitor[3] - main_monitor[1]
            return f"M{len(monitors)}_{w}x{h}"
        except Exception as e:
            logger.error(f"Failed to generate hardware fingerprint: {e}")
            return "Unknown"

    def auto_detect_profile(self) -> str:
        """Attempts to match current fingerprint to an existing profile."""
        fingerprint = self.get_current_fingerprint()
        # Look for a profile with a matching geometry
        target_geometry = fingerprint.split('_')[1] if '_' in fingerprint else ""
        
        for name, p in self.profiles.items():
            if p.get("screen_geometry") == target_geometry:
                logger.info(f"Auto-detected profile: {name} (matches {target_geometry})")
                return name
        return self.current_profile_name

    def get_active_calibration(self) -> Dict:
        """Retrieves calibration data for the active profile."""
        p = self.profiles.get(self.current_profile_name, {})
        # Return default if not found
        return p.get("calibration", {
            "dock_rect": {"x": 0, "y": 0, "width": 1920, "height": 1080},
            "dpi_offset_y": 140
        })

    def update_calibration(self, dock_rect: Dict, dpi_offset: int = 140) -> None:
        """Updates calibration parameters for the active profile."""
        if self.current_profile_name not in self.profiles:
            fingerprint = self.get_current_fingerprint()
            geometry = fingerprint.split('_')[1] if '_' in fingerprint else "Unknown"
            self.profiles[self.current_profile_name] = {
                "device_name": "New Device",
                "screen_geometry": geometry,
                "calibration": {}
            }
        
        self.profiles[self.current_profile_name]["calibration"] = {
            "dock_rect": dock_rect,
            "dpi_offset_y": dpi_offset
        }
        self.profiles[self.current_profile_name]["last_updated"] = time.time()
        self.save_profiles()

    def switch_profile(self, name: str) -> bool:
        """Switches the active profile."""
        if name in self.profiles:
            self.current_profile_name = name
            logger.info(f"Switched to profile: {name}")
            self.save_profiles()
            return True
        logger.warning(f"Profile '{name}' not found.")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hw = HardwareManager()
    print(f"Current Fingerprint: {hw.get_current_fingerprint()}")
    print(f"Active Calibration: {hw.get_active_calibration()}")
