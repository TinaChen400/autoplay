import time
import random
import cv2
import pyautogui
import win32gui
import win32con
import os
import difflib

class VisualSkillsMixin:
    def dock_target_window(self):
        """[V4.1] 核心吸附逻辑：强制稳定目标窗口"""
        self._log("Starting window docking...")
        hwnd = self.wm.find_remote_window()
        if not hwnd:
            self._log("Error: Target window not found!")
            return False
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 10, 10, 0, 0, 
                                 win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            time.sleep(1.0) 
            self._log(f"Window docked successfully at (10, 10). HWND: {hwnd}")
            return True
        except Exception as e:
            self._log(f"Docking failed: {e}")
            return False

    def click_landmark(self, keywords, optional=False, offset_x=0, offset_y=0):
        """视觉地标对位点击 (支持 X/Y 偏移)"""
        self._log(f"Executing click_landmark: {keywords} (Offset: {offset_x}, {offset_y})")
        if not self.dock_target_window():
            self._log("Warning: Could not dock window, proceeding anyway...")
            
        rect_data = self.wm.get_window_rect()
        # [V7.31] 视野裁剪：向下偏移 150 像素，完美避开浏览器标签和地址栏干扰
        crop_top = 150
        region = { 
            "top": rect_data["top"] + crop_top, 
            "left": rect_data["left"], 
            "width": rect_data["width"], 
            "height": rect_data["height"] - crop_top 
        } if rect_data else None
        
        view_path = self.vc.capture_screen(region=region)
        img = cv2.imread(view_path)
        if img is None: return False
        
        reader = self.vc.get_ocr().reader
        results = reader.readtext(img)
        
        target_pos = None
        for res in results:
            text = res[1].lower().strip()
            # [V7.26] 模糊匹配策略：只要相似度超过 0.7 就算中
            is_match = False
            if any(k.lower() in text for k in keywords):
                is_match = True
            else:
                for k in keywords:
                    matches = difflib.get_close_matches(k.lower(), [text], n=1, cutoff=0.7)
                    if matches:
                        is_match = True
                        self._log(f"Fuzzy Matched: '{text}' matched to keyword '{k}'")
                        break
            
            if is_match:
                cx = int((res[0][0][0] + res[0][1][0]) / 2)
                # [V7.31] 加上裁剪掉的偏移量
                cy = int((res[0][0][1] + res[0][2][1]) / 2) + crop_top
                target_pos = (cx, cy)
                break
        
        if target_pos:
            rect = self.wm.get_window_rect()
            win_x = rect["left"] if rect else 10
            win_y = rect["top"] if rect else 10
            
            # [V7.33] 最终坐标 = 窗口起始 + 地标相对 + 用户偏移
            final_x = win_x + target_pos[0] + offset_x
            final_y = win_y + target_pos[1] + offset_y
            
            # [V7.30] 改用 win32api 物理点击
            import win32api, win32con
            win32api.SetCursorPos((final_x, final_y))
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self._log(f"Hard-clicked landmark at ({final_x}, {final_y})")
            return True
        
        # [V7.25] 失败时的“黑匣子”数据保存
        debug_path = os.path.join(self.root, "records", "ocr_failed_debug.jpg")
        cv2.imwrite(debug_path, img)
        self._log(f"!!! [OCR_FAIL] 未找到关键词 {keywords}。调试图已存至: {debug_path}")
        
        # 打印出所有识别到的片段，帮你分析
        all_text = [res[1] for res in results]
        self._log(f"系统看到的内容摘要: {all_text[:10]}...")
        
        return optional

    def robust_click_landmark(self, keywords, engines=["easyocr", "paddleocr"], verify=True):
        """[V4.2] 鲁棒点击：多引擎识别 + 视觉前后对比校验"""
        self._log(f"Executing robust_click_landmark: {keywords}")
        before_path = self.vc.capture_screen()
        img = cv2.imread(before_path)
        target_pos = self.expert.find_landmark(img, keywords, engines=engines)
        
        if not target_pos:
            self._log("Error: Target not found by any engine.")
            return False
            
        rect = self.wm.get_window_rect()
        offset_x, offset_y = (rect["left"], rect["top"]) if rect else (10, 10)
        abs_x, abs_y = target_pos[0] + offset_x, target_pos[1] + offset_y
        
        pyautogui.moveTo(abs_x, abs_y, duration=0.3)
        pyautogui.click()
        
        if not verify: return True
        time.sleep(1.0)
        after_path = self.vc.capture_screen()
        diff_score = self.vc.compare_images(before_path, after_path)
        
        self._log(f"Visual Diff Score: {diff_score:.2f}%")
        return diff_score > 3.0

    def zoom_pan_cruise(self, keywords, scroll_amount=[3, 6], pan_dx=0, pan_dy=0, offset_x=0, offset_y=350):
        """[V7.37] 物理巡航：地标对位 -> 移动到图片中心 -> 滚轮缩放 -> 物理平移"""
        # 1. 寻找并点击地标 (比如点击 "Response A" 标签来确保该区域获得焦点)
        # 默认不传偏移给 click_landmark，点击完后再移动，或者也可以直接传
        if self.click_landmark(keywords):
            time.sleep(0.5)
            import win32api, win32con
            
            # 2. 自动移动到图片中心 (从地标位置偏移)
            if offset_y != 0 or offset_x != 0:
                curr_x, curr_y = win32api.GetCursorPos()
                win32api.SetCursorPos((curr_x + offset_x, curr_y + offset_y))
                time.sleep(0.2)
                self._log(f"Moved mouse to image center with offset ({offset_x}, {offset_y})")
            
            # 3. 缩放 (滚轮) - [V7.37] 纯滚轮模式，不带 Ctrl，避免网页整体缩放
            clicks = random.randint(scroll_amount[0], scroll_amount[1]) if isinstance(scroll_amount, list) else scroll_amount
            for _ in range(clicks):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
                time.sleep(0.05)
            self._log(f"Zoomed in with {clicks} wheel clicks.")
            
            # 4. 平移 (物理拖拽)
            if pan_dx != 0 or pan_dy != 0:
                time.sleep(0.3)
                curr_x, curr_y = win32api.GetCursorPos()
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.1)
                
                # 分步平移，更拟人
                steps = 10
                for i in range(1, steps + 1):
                    target_x = curr_x + int(pan_dx * i / steps)
                    target_y = curr_y + int(pan_dy * i / steps)
                    win32api.SetCursorPos((target_x, target_y))
                    time.sleep(0.02)
                    
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self._log(f"Cruised with pan ({pan_dx}, {pan_dy})")
            return True
        return False

    def action_click_landmark(self, keywords, optional=False):
        return self.click_landmark(keywords, optional)

    def action_screenshot(self, label="snap"):
        return self.vc.capture_screen()
