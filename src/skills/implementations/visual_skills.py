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
        no_click = kwargs.get("no_click", False)
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
            # [V32.8] 智能预判：先确定任务类型
            is_response_task = any("response" in k.lower() for k in keywords)
            target_is_b = any("b" in k.lower() for k in keywords)
            
            # Global scan for all matches containing 'Response'
            all_matches = []
            detailed_results = ocr.get_detailed_results(frame_np)
            
            for (bbox, text, prob) in detailed_results:
                # [V18.8] 极致模糊匹配：只要识别到超过 3 个字母的词根即命中
                clean_t = "".join(filter(str.isalnum, text.lower()))
                
                match_found = False
                for kw in keywords:
                    clean_kw = "".join(filter(str.isalnum, kw.lower()))
                    # [V32.8] 唤醒专用补丁：非 Response 任务采取最宽松匹配
                    if not is_response_task:
                        if len(clean_kw) >= 3 and clean_kw[:3] in clean_t:
                            match_found = True
                            break
                        elif clean_kw in clean_t:
                            match_found = True
                            break
                    else:
                        # Response 任务维持严格 A/B 校验
                        if clean_kw == clean_t:
                            match_found = True
                            break
                        elif len(clean_kw) >= 3 and clean_kw[:3] in clean_t:
                            if ("a" in clean_kw and "a" not in clean_t) or ("b" in clean_kw and "b" not in clean_t):
                                continue
                            match_found = True
                            break
                
                if match_found:
                    cx = int(np.mean([p[0] for p in bbox]))
                    cy = int(np.mean([p[1] for p in bbox]))
                    self._log(f"Matched Anchor: '{text}' at ({cx}, {cy})")
                    all_matches.append({"x": cx, "y": cy, "text": text})
            
            # [V32.3] 垂直优先对位：按 Y 轴（从上到下）排序，优先锁定最顶部的标题
            all_matches = sorted(all_matches, key=lambda m: m["y"])
            
            if not all_matches:
                # [DEBUG] 打印全量识别结果
                all_text = [res[1] for res in detailed_results]
                self._log(f"DEBUG: No matches found for {keywords}. All visible text: {all_text}")
                return False
            
            # [V32.5] 智能分流补丁：只有在明确寻找 Response A/B 时才启用 X 轴过滤
            is_response_task = any("response" in k.lower() for k in keywords)
            target_is_b = any("b" in k.lower() for k in keywords)
            
            if len(all_matches) >= 2 and is_response_task:
                if target_is_b:
                    # 寻找右侧的 B
                    right_matches = [m for m in all_matches if m["x"] > 600]
                    found_pos = (right_matches[0]["x"], right_matches[0]["y"]) if right_matches else (all_matches[0]["x"], all_matches[0]["y"])
                else:
                    # 寻找左侧的 A
                    left_matches = [m for m in all_matches if m["x"] < 600]
                    found_pos = (left_matches[0]["x"], left_matches[0]["y"]) if left_matches else (all_matches[0]["x"], all_matches[0]["y"])
            else:
                # 普通任务（如 Inputs）或只有一个匹配时，直接取最顶部的那个
                found_pos = (all_matches[0]["x"], all_matches[0]["y"])
                if len(all_matches) == 1:
                    self._log(f"Visual Split: Single TOP Anchor found at {found_pos}")
                else:
                    self._log(f"Visual Split: Top-most generic anchor found at {found_pos}")
        
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
        if no_click:
            return {"x": target_x, "y": target_y}

        smooth_move(target_x, target_y, duration=0.5)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        return {"x": target_x, "y": target_y}

    def zoom_pan_cruise(self, keywords, **kwargs):
        """
        [V18.6] High-intensity humanoid cruise with Stationary Fallback.
        """
        self._log(f"Starting V18.6 Smart Cruise for: {keywords}")
        
        # 1. 尝试找锚点对位
        found_pos = self.click_landmark(keywords, no_click=True)
        
        if found_pos:
            tx, ty = found_pos["x"], found_pos["y"]
            self._log(f"Cruise anchor locked at ({tx}, {ty}).")
            # [V32.4] 修复：使用顶层已导入的 win32api 执行点击
            smooth_move(tx, ty, duration=0.3)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            self._log("Cruise anchor not found. Using stationary cruise at current position.")
            tx, ty = win32api.GetCursorPos()
            
        time.sleep(0.8)
        start_x, start_y = tx, ty
        
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
        
        scroll_range = kwargs.get("scroll_amount", [8, 15])
        # [V18.9] 兼容性补丁：支持单数字或范围数组
        if isinstance(scroll_range, (int, float)):
            scroll_range = [int(scroll_range), int(scroll_range)]
            
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
