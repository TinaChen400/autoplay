# -*- coding: utf-8 -*-
"""
ViewportManager: Handles coordinate mapping and window alignment.
"""

import os
import json
import logging
import ctypes
from typing import Dict, Tuple, Optional

# --- CRITICAL: FORCE DPI AWARENESS BEFORE ANY UI OR WIN32 CALLS ---
try:
    # Set DPI Awareness to Per-Monitor V2 (2)
    # This must be done before any window creation
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
# -----------------------------------------------------------------

# Set up logging
logger = logging.getLogger("ViewportManager")
logger.setLevel(logging.INFO)

class ViewportManager:
    """
    ViewportManager handles the mapping between relative (percentage) coordinates
    and absolute screen coordinates based on the docked window position.
    """
    
    def __init__(self, config_path: str = None):
        # Default config path relative to project root
        if config_path is None:
            self.config_path = os.path.join(os.getcwd(), 'config', 'viewport_config.json')
        else:
            self.config_path = config_path
            
        self.config = {}
        self.dock_rect = None      # Actual docked window rect {x, y, width, height}
        self.base_resolution = (1920, 1080)  # Standard base resolution
        self.scale_factor = 1.0
        self.locked = False
        
        self.load_config()

    def load_config(self) -> None:
        """Loads viewport and calibration settings from JSON."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config not found at {self.config_path}, using defaults.")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            vp = self.config.get('viewport', {})
            self.base_resolution = (vp.get('width', 1920), vp.get('height', 1080))
            
            calib = self.config.get('calibration', {})
            self.dock_rect = calib.get('dock_rect')
            self.scale_factor = calib.get('scale_factor', 1.0)
            
            logger.debug(f"Config loaded. Base resolution: {self.base_resolution}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def save_config(self) -> None:
        """Saves current calibration settings to JSON."""
        try:
            self.config['calibration'] = {
                'dock_rect': self.dock_rect,
                'scale_factor': self.scale_factor
            }
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("Config saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update_dock_rect(self, rect: Dict[str, int]) -> None:
        """Updates the docked window area and recalculates scale factor."""
        self.dock_rect = rect
        if self.base_resolution[0] > 0:
            # Scale factor based on width change
            self.scale_factor = rect['width'] / self.base_resolution[0]
            
        logger.info(f"Dock updated: {rect}, Scale Factor: {self.scale_factor:.2f}")
        self.save_config()

    def set_dock_from_hardware(self) -> None:
        """Pulls dock rect from HardwareManager's active calibration."""
        try:
            from src.utils.hardware_manager import HardwareManager
            hw = HardwareManager()
            calib = hw.get_active_calibration()
            if calib and 'dock_rect' in calib:
                self.update_dock_rect(calib['dock_rect'])
            else:
                logger.error("No active calibration found in HardwareManager.")
        except ImportError:
            logger.error("HardwareManager not found. Cannot pull dock rect.")

    def to_absolute(self, x_percent: float, y_percent: float) -> Tuple[int, int]:
        """
        Converts percentage coordinates (0-100) to absolute screen coordinates.
        ALWAYS reloads config to handle moved windows.
        """
        self.load_config() # <--- Real-time sync with visual_dock
        
        if not self.dock_rect:
            logger.warning("dock_rect not set, returning (0,0)")
            return (0, 0)
            
        abs_x = int(self.dock_rect['x'] + (x_percent * self.dock_rect['width'] / 100))
        abs_y = int(self.dock_rect['y'] + (y_percent * self.dock_rect['height'] / 100))
        return (abs_x, abs_y)

    def to_percentage(self, abs_x: int, abs_y: int) -> Tuple[float, float]:
        """Converts absolute screen coordinates to percentage of current dock."""
        if not self.dock_rect:
            return (0.0, 0.0)
            
        x_pct = (abs_x - self.dock_rect['x']) / self.dock_rect['width'] * 100
        y_pct = (abs_y - self.dock_rect['y']) / self.dock_rect['height'] * 100
        return (x_pct, y_pct)

    def get_status(self) -> Dict:
        """Returns current viewport status."""
        return {
            'base_resolution': f"{self.base_resolution[0]}x{self.base_resolution[1]}",
            'current_dock': self.dock_rect,
            'scale_factor': self.scale_factor,
            'config_path': self.config_path
        }

if __name__ == "__main__":
    # Basic test
    logging.basicConfig(level=logging.INFO)
    vm = ViewportManager()
    vm.update_dock_rect({'x': 100, 'y': 100, 'width': 1000, 'height': 1000})
    print(f"50%, 50% -> {vm.to_absolute(50, 50)}")
