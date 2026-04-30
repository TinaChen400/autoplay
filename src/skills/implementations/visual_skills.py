import time
import win32api
import win32con
import pyautogui
import os
import random
import math
from src.skills.humanize import smooth_move

class VisualSkillsMixin:
    """
    [V18.6] Visual Skills Engine: Supports multi-anchor alignment and A/B splitting.
    """
    
    def click_landmark(self, keywords, offset_x=0, offset_y=0, **kwargs):
        """
        [V18.6] Humanoid visual click with A/B side detection logic.
        """
        import cv2
        import numpy as np
        
        # 1. Get window rect
        rect = self.wm.get_window_rect()
        win_px, win_py = rect['left'], rect['top']
        
        from src.vision.capture import VisionCapture
        vc = VisionCapture()
        ocr = vc.get_ocr()
        frame_np = vc.capture_dock_region({"x": win_px, "y": win_py, "width": rect['width'], "height": rect['height']})
        
        found_pos = None
        if frame_np is not None:
            # Global scan for all matches containing 'Response'
            all_matches = []
            detailed_results = ocr.get_detailed_results(frame_np)
            
            for (bbox, text, prob) in detailed_results:
                clean_t = text.lower().replace(" ", "")
                # Check if any provided keyword (lowered and stripped) is in the detected text
                match_found = False
                for kw in keywords:
                    if kw.lower().replace(" ", "") in clean_t:
                        match_found = True
                        break
                
                if match_found:
                    cx = int(np.mean([p[0] for p in bbox]))
                    cy = int(np.mean([p[1] for p in bbox]))
                    all_matches.append({"x": cx, "y": cy, "text": text})
            
            # Sort by X coordinate (Left to Right)
            all_matches = sorted(all_matches, key=lambda m: m["x"])
            
            # Intelligent splitting for A vs B
            target_is_b = any("b" in k.lower() for k in keywords)
            
            if len(all_matches) >= 2:
                if target_is_b:
                    # Target B: Pick the rightmost one
                    found_pos = (all_matches[-1]["x"], all_matches[-1]["y"])
                    self._log(f"Visual Split: Locked Right Anchor (Response B) at {found_pos}")
                else:
                    # Target A: Pick the leftmost one
                    found_pos = (all_matches[0]["x"], all_matches[0]["y"])
                    self._log(f"Visual Split: Locked Left Anchor (Response A) at {found_pos}")
            elif len(all_matches) == 1:
                # Only one found, use it regardless but log correctly
                found_pos = (all_matches[0]["x"], all_matches[0]["y"])
                tag = "Response B" if target_is_b else "Response A"
                self._log(f"Visual Split: Single Anchor found, assuming {tag} at {found_pos}")
        
        if not found_pos:
            return False

        scale = 1.0 
        
        # Humanoid jitter and physical coordinate calculation
        target_x = int((win_px + found_pos[0]) / scale) + offset_x + random.randint(-5, 5)
        target_y = int((win_py + found_pos[1]) / scale) + offset_y + random.randint(-5, 5)
        
        # Safety boundary lock
        target_x = max(win_px + 20, min(target_x, win_px + rect['width'] - 20))
        target_y = max(win_py + 20, min(target_y, win_py + rect['height'] - 20))
        
        # Humanoid execution (Move + Pause + Click)
        smooth_move(target_x, target_y, duration=0.5)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        return True

    def zoom_pan_cruise(self, keywords, **kwargs):
        """
        [V18.6] High-intensity humanoid cruise with A/B discrimination.
        """
        self._log(f"Starting V18.6 Smart Cruise for: {keywords}")
        if not self.click_landmark(keywords, offset_y=150): 
            self._log("Cruise anchor not found. Skipping to avoid drift.")
            return False 
        
        time.sleep(0.8) 
        
        start_x, start_y = win32api.GetCursorPos()
        self._log(f"Cruise Start Location: ({start_x}, {start_y})")
        
        # Parameters
        scroll_range = kwargs.get("scroll_amount", [8, 15])
        
        # 允许 JSON 传入范围，比如 [30, 80] 或 "30-80"
        def _parse_pan(val, default):
            if val is None: return default
            if isinstance(val, list) and len(val) == 2: return random.randint(int(val[0]), int(val[1]))
            if isinstance(val, str) and "-" in val:
                p = val.split("-")
                return random.randint(int(p[0]), int(p[1]))
            return int(val)
            
        pan_dx = _parse_pan(kwargs.get("pan_dx"), 60)
        pan_dy = _parse_pan(kwargs.get("pan_dy"), 40)
        
        rect = self.wm.get_window_rect()
        steps = random.randint(scroll_range[0], scroll_range[1])
        self._log(f"Executing {steps} cruise cycles (Zoom + Smooth Pan)...")
        
        current_zoom = 0
        for i in range(steps):
            # 1. Randomized Zoom Strategy
            # Decision: Zoom In, Zoom Out, or Stay?
            zoom_choice = random.random()
            if zoom_choice < 0.4: # Zoom In
                scroll_val = 120 * random.randint(1, 3)
                current_zoom += 1
            elif zoom_choice < 0.7: # Zoom Out
                scroll_val = -120 * random.randint(1, 2)
                current_zoom -= 1
            else: # Jitter Zoom
                scroll_val = random.choice([120, -120])
            
            # Execute multiple wheel events for more 'drama' if choosing to zoom
            repeat_zoom = random.randint(1, 2) if abs(scroll_val) > 120 else 1
            for _ in range(repeat_zoom):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, scroll_val, 0)
                time.sleep(0.1)
            
            time.sleep(0.4) 
            
            # 2. Dynamic Panning based on Zoom level
            # If we are "zoomed in", pan more aggressively to look around
            pan_multiplier = 1.5 if current_zoom > 0 else 1.0
            
            angle = (i / steps) * 2 * math.pi
            osc_x = int(math.cos(angle) * 50 * pan_multiplier) 
            osc_y = int(math.sin(angle) * 35 * pan_multiplier)
            
            # Base target with increased random 'exploration' jitter
            target_x = start_x + pan_dx + osc_x + random.randint(-20, 20)
            target_y = start_y + pan_dy + osc_y + random.randint(-20, 20)
            
            # Stay within image area
            target_x = max(rect['left'] + 80, min(target_x, rect['left'] + rect['width'] - 80))
            target_y = max(rect['top'] + 80, min(target_y, rect['top'] + rect['height'] - 80))
            
            self._log(f"Cruise Step {i+1}/{steps}: Zoom({current_zoom}) Moving to ({target_x}, {target_y})")
            
            # 3. Simulated Reading/Observation Pause
            # If zoomed in, occasionally pause longer to "look"
            move_duration = random.uniform(0.4, 0.8)
            smooth_move(target_x, target_y, duration=move_duration)
            
            pause_time = random.uniform(0.6, 1.2)
            if current_zoom > 1: pause_time += 1.0 # Look longer when zoomed in
            time.sleep(pause_time)
            
        self._log(f"V18.6 Cruise completed successfully.")
        return True
