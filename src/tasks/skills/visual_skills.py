import time
import random
import cv2
import pyautogui
import win32gui
import win32con

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

    def click_landmark(self, keywords, optional=False):
        """视觉地标对位点击"""
        self._log(f"Executing click_landmark: {keywords}")
        if not self.dock_target_window():
            self._log("Warning: Could not dock window, proceeding anyway...")
            
        rect_data = self.wm.get_window_rect()
        region = { "top": rect_data["top"], "left": rect_data["left"], "width": rect_data["width"], "height": rect_data["height"] } if rect_data else None
        
        view_path = self.vc.capture_screen(region=region)
        img = cv2.imread(view_path)
        if img is None: return False
        
        reader = self.vc.get_ocr().reader
        results = reader.readtext(img)
        
        target_pos = None
        for res in results:
            text = res[1].lower()
            if any(k.lower() in text for k in keywords):
                cx = int((res[0][0][0] + res[0][1][0]) / 2)
                cy = int((res[0][0][1] + res[0][2][1]) / 2)
                target_pos = (cx, cy)
                break
        
        if target_pos:
            rect = self.wm.get_window_rect()
            offset_x = rect["left"] if rect else 10
            offset_y = rect["top"] if rect else 10
            abs_x, abs_y = target_pos[0] + offset_x, target_pos[1] + offset_y
            pyautogui.moveTo(abs_x, abs_y, duration=0.5)
            pyautogui.click()
            return True
        
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

    def zoom_pan_cruise(self, landmark_keywords, scroll_amount=[3, 6], pan_dx=0, pan_dy=0):
        """暴力巡航：缩放 + 平移"""
        if self.click_landmark(landmark_keywords):
            time.sleep(0.5)
            import win32api
            clicks = random.randint(scroll_amount[0], scroll_amount[1]) if isinstance(scroll_amount, list) else scroll_amount
            for _ in range(clicks):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
                time.sleep(0.05)
            if pan_dx != 0 or pan_dy != 0:
                time.sleep(0.2)
                curr_x, curr_y = win32api.GetCursorPos()
                pyautogui.dragTo(curr_x + pan_dx, curr_y + pan_dy, duration=0.8, button='left')
            return True
        return False

    def action_click_landmark(self, keywords, optional=False):
        return self.click_landmark(keywords, optional)

    def action_screenshot(self, label="snap"):
        return self.vc.capture_screen()
