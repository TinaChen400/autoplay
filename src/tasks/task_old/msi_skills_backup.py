import sys
import json
import os
import cv2
import time
import numpy as np
import mss
import win32gui
import win32con
import win32api
import random

sys.path.append(r"D:/Dev/autoplay")
from src.utils.vision import VisionCapture
from src.utils.ocr_reader import OCRReader
from src.execution.remote_agent import RemoteAgent
from src.utils.hardware_manager import HardwareManager
from src.utils.layout_parser import LayoutParser

from src.utils.window_lock import WindowManager
from src.tasks.skill_gpt_oracle import GPTOracle

class MSISkills:
    """
    MSI 鍘熷瓙鎶€鑳界Н鏈ㄥ簱 (V27: LLM Integrated)
    """
    def __init__(self, bridge=None):
        self.bridge = bridge
        self.agent = RemoteAgent()
        self.vc = VisionCapture()
        self.ocr = OCRReader()
        self.records_dir = r"D:/Dev/autoplay/records"
        self.hw = HardwareManager()
        self.wm = WindowManager(["Tina", "MSI"])
        self.oracle = GPTOracle(bridge=bridge) 

    def action_llm_send(self, prompt=None):
        """
        姝ラ 1: 鎶曞杺鎴浘涓庢寚浠よ嚦璞嗗寘/GPT (V28.3)
        """
        if prompt is None:
            # 浣跨敤榛樿鎻愮ず璇?            prompt = self.oracle.system_prompt
            
        print("[SKILL] 姝ｅ湪鎶曞杺 UI 鎴浘涓庢寚浠よ嚦璞嗗寘/GPT...")
        
        # 1. 鐗╃悊浣嶇疆鍑嗗 (鍔犺浇褰撳墠 Tina 鍧愭爣)
        config = self._load_config()
        if not config or "dock_rect" not in config:
            print("[SKILL] 閿欒: 鏈牎鍑?Dock 鍧愭爣锛屾棤娉曟埅鍥?)
            return False
            
        dock_rect = config["dock_rect"]
        
        # 2. 鎴浘骞跺瓨鍏ュ壀璐存澘
        if not self.oracle.action_capture_to_clipboard(dock_rect):
            return False
            
        # 3. 鍞よ捣娴忚鍣ㄥ苟鍙戦€?        if not self.oracle.action_focus_gpt_window():
            return False
            
        if not self.oracle.action_send_to_gpt(prompt):
            return False
        return True

    def action_llm_extract_click(self):
        """
        姝ラ 2: 鎶撳彇 LLM 缁撴灉骞舵墽琛岀偣鍑?(V28.1 浼樺寲鐗?
        """
        print("[SKILL] 鍚姩瑙嗚鎻愬彇寮曟搸...")
        decision = self.oracle.action_extract_decision(self.ocr)
        
        # 绔嬪嵆鍙嶉鑷?UI
        if self.bridge:
            for step in self.bridge.steps:
                if step.methodName == "action_llm_extract_click":
                    step.result_data = f"{decision}" if decision else "璇嗗埆澶辫触"
                    break
            
            # 寮哄埗閫氱煡 UI 鍒锋柊
            if hasattr(self.bridge, 'on_step_added_cb') and self.bridge.on_step_added_cb: 
                self.bridge.on_step_added_cb()

        if not decision:
            print("[SKILL] LLM 鏈兘缁欏嚭鏈夋晥鍐崇瓥")
        # 杩欓噷鐨勫喅绛?A/B 闇€瑕佹槧灏勫埌 action_click_smart 鐨勫叧閿瓧
        keyword = f"Response {decision}"
        print(f"[SKILL] GPT 鏈€缁堝喅绛? {decision} -> 灏濊瘯鐐瑰嚮 '{keyword}'")
        
        # 鑷姩鍒囨崲鍥?Tina 绐楀彛 (閫氳繃 WindowManager)
        hwnd = win32gui.FindWindow(None, "Tina")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            
        return self.action_click_smart(keywords=[keyword])

    def _save_dock_rect(self, x, y, w, h):
        """鐢?UI 瀹炴椂璋冪敤鐨勫悓姝ユ帴鍙ｏ紝鏇存柊鐗╃悊瀵逛綅鍩哄噯"""
        dock_rect = {"x": x, "y": y, "width": w, "height": h}
        # 鐩存帴閫氳繃纭欢绠＄悊鍣ㄤ繚瀛橈紝纭繚鍏ㄥ眬涓€鑷存€?        self.hw.update_calibration(dock_rect=dock_rect)

    def _load_config(self):
        """浠庢椿璺冪幆澧冩。妗堝姞杞藉熀鍑嗗弬鏁?""
        return self.hw.get_active_calibration()

    def action_screenshot(self, label="view"):
        """鍘熷瓙绉湪锛氭媿鎽勭墿鐞嗗浣嶅揩鐓э紙V14.5 楂樺垎灞忓吋瀹圭増锛?""
        config = self._load_config()
        dock_rect = None
        if config:
            raw = config.get("dock_rect")
            # 琛ヤ竵锛氱‘淇濆潗鏍囦负鏁存暟涓斿湪鍚堣鑼冨洿鍐?            dock_rect = {
                "left": int(raw["x"]), 
                "top": int(raw["y"]), 
                "width": int(raw["width"]), 
                "height": int(raw["height"])
            }
        
        with mss.mss() as sct:
            # 楂樺垎灞忚ˉ涓侊細鐩存帴鎶撳彇鎸囧畾鐨勭墿鐞嗗潗鏍囩煩褰紝涓嶉拡瀵瑰崟涓?monitor 绱㈠紩
            try:
                screenshot = sct.grab(dock_rect) if dock_rect else sct.grab(sct.monitors[0])
                save_path = os.path.join(self.records_dir, f"snap_{label}.jpg")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
                print(f"[SKILL] 蹇収淇濆瓨: {save_path} (Region: {dock_rect})")
                return save_path
            except Exception as e:
                print(f"[SKILL] 鎴浘澶辫触锛屽洖鍒囨ā寮? {e}")
                screenshot = sct.grab(sct.monitors[0])
                save_path = os.path.join(self.records_dir, f"snap_{label}_fallback.jpg")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
                return save_path

    def action_click_template(self, template_name="zoom_icon", threshold=0.6, roi=None, **kwargs):
        """[V36.1] AI 视觉对位：模板匹配 + V81 地标补扫"""
        import cv2, numpy as np, os
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", f"{template_name}.png")
        if not os.path.exists(template_path):
            return self.action_click_near_landmark(**kwargs)
        view_path = self.action_screenshot("vision_search")
        screen_img = cv2.imread(view_path)
        template_img = cv2.imread(template_path)
        if screen_img is None or template_img is None: return False
        gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(cv2.Canny(gray_screen, 50, 150), cv2.Canny(gray_template, 50, 150), cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            print(f"  - [Vision Success] Icon matched: {max_val:.2f}")
            tw, th = template_img.shape[1], template_img.shape[0]
            return self._physical_click(max_loc[0] + tw // 2, max_loc[1] + th // 2)
        else:
            return self.action_click_near_landmark(**kwargs)

    def _physical_click(self, x, y, debug_rect=None):
        """[V81.0] 物理点击驱动：支持 V81 视觉回显"""
        import pyautogui, time, os, cv2, numpy as np
        config = self._load_config()
        base_x, base_y = config["dock_rect"]["x"], config["dock_rect"]["y"]
        target_x, target_y = int(base_x + x), int(base_y + y)
        try:
            diag_path = os.path.join(self.records_dir, "click_diagnostic_V62_PRO.jpg")
            snap_path = os.path.join(self.records_dir, "v81_full_scan.jpg")
            if not os.path.exists(snap_path): snap_path = os.path.join(self.records_dir, "vision_search.jpg")
            debug_img = cv2.imread(snap_path) if os.path.exists(snap_path) else np.zeros((1080, 1920, 3), dtype=np.uint8)
            if debug_rect:
                rx, ry, rw, rh = debug_rect
                cv2.rectangle(debug_img, (int(rx), int(ry)), (int(rx + rw), int(ry + rh)), (0, 255, 0), 3)
            cv2.circle(debug_img, (200, 200), 100, (255, 255, 255), -1)
            cv2.putText(debug_img, "V81 ACTIVE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 5)
            draw_x, draw_y = int(target_x - base_x), int(target_y - base_y)
            cv2.drawMarker(debug_img, (draw_x, draw_y), (0, 0, 255), cv2.MARKER_CROSS, 60, 4)
            cv2.imwrite(diag_path, debug_img)
        except Exception as e: print(f"  - [Diag Error] {e}")
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        time.sleep(0.1); pyautogui.click(); return True

    def action_click_near_landmark(self, anchor_keywords=["Response A"], offset_x=0, offset_y=65, roi=None, **kwargs):
        """[V81.0 暴力全屏版] 彻底抛弃 ROI，全屏模糊语义搜索"""
        import pyautogui, time, cv2, numpy as np
        print(f">>> V81 EXECUTING: FULL SCREEN SCAN <<<")
        pyautogui.press('esc'); time.sleep(0.5)
        self.agent.activate_window(self.agent.profile_name)
        view_path = self.action_screenshot("v81_full_scan")
        img = cv2.imread(view_path)
        if img is None: return False
        ocr_res = self.ocr.reader.readtext(img)
        candidates = []
        for r in ocr_res:
            text = r[1].lower().replace(" ", "")
            if "respon" in text and "a" in text:
                cx, cy = ((r[0][0][0] + r[0][1][0]) / 2) / 1.5, ((r[0][0][1] + r[0][2][1]) / 2) / 1.5
                if cy > 400: candidates.append((cx, cy, r[1]))
        if not candidates:
            print(f"  - [V81 ERROR] 未找到地标！")
            return False
        candidates.sort(key=lambda x: x[1])
        ax, ay = candidates[0][0], candidates[0][1]
        print(f"  - [V81 HIT] 锁定地标: {candidates[0][2]} at ({ax:.0f}, {ay:.0f})")
        tx_rel, ty_rel, best_rect = self._detect_action_zone(ax, ay, img)
        if tx_rel and ty_rel:
            return self._physical_click(tx_rel, ty_rel, debug_rect=best_rect)
        return self._physical_click(ax + offset_x, ay + offset_y)
    def action_click_landmark_v2(self, keywords=["Inputs", "Earnings"], search_depth=400, optional=False):
        """鍘熷瓙绉湪 V2锛氳涔夌骇瑙嗚鍚搁檮鎺㈡祴 (瀹為獙鎬ф柟妗?"""
        print(f"[SKILL-V2] 鍚姩璇箟瑙嗚鎼滅储锛岀洰鏍囬敋鐐? {keywords}")
        
        import win32gui, win32api, win32con
        import numpy as np

        # 1. 寮哄姏瀵圭劍閿佸畾
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except: pass

        # 2. 鐘舵€佸揩鐓?        view_path = self.action_screenshot("semantic_search")
        img = cv2.imread(view_path)
        if img is None: return False
        
        # 3. OCR 閿氱偣瀹氫綅
        context = self.ocr.read_screen(img)
        ax, ay = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in keywords):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    cur_ax, cur_ay = int(parts[0]), int(parts[1])
                    if cur_ay < 160 or cur_ax < 20: continue # 娌跨敤闃茶瑙︾鍖?                    ax, ay = cur_ax, cur_ay
                    print(f"[SKILL-V2] 鐗╃悊閿氱偣閿佸畾: '{line}' at ({ax}, {ay})")
                    break
                except: continue
        
        if ay == -1:
            if optional: return True
            print(f"[SKILL-V2] 閿氱偣鏈锛屾悳绱㈠け璐ャ€?)
            return False

        # 4. 璇箟瑙嗚鎺㈡祴 (OpenCV 榄旀硶鏃堕棿)
        h, w, _ = img.shape
        # 瀹氫箟鎼滅储鎵囧尯: 鏂囧瓧姝ｄ笅鏂?400px锛屽乏鍙冲悇鎵╂暎 200px
        roi_y1, roi_y2 = ay, min(ay + search_depth, h)
        roi_x1, roi_x2 = max(ax - 50, 0), min(ax + 350, w)
        roi = img[roi_y1:roi_y2, roi_x1:roi_x2]
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        dilated = cv2.dilate(edged, None, iterations=1)
        contours, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        debug_img = roi.copy()
        for cnt in contours:
            x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            # 杩囨护閫昏緫锛氱鍚堝浘鏍?鍗＄墖澶у皬锛屼笖涓嶈兘澶墎鎴栧お缁?            if 1000 < area < 40000 and 0.4 < (w_c/h_c) < 2.5:
                # 璁＄畻涓庨敋鐐规枃瀛楀簳杈圭紭鐨勮窛绂伙紙瓒婅繎瓒婂ソ锛?                dist = y_c 
                candidates.append({
                    'center': (x_c + w_c//2, y_c + h_c//2),
                    'dist': dist,
                    'rect': (x_c, y_c, w_c, h_c)
                })
                cv2.rectangle(debug_img, (x_c, y_c), (x_c+w_c, y_c+h_c), (255, 0, 0), 2)

        final_tx, final_ty = -1, -1
        if candidates:
            # 鎺掑簭瀵绘壘鏈€绗﹀悎鈥滅揣閭绘枃瀛椾笅鏂光€濈壒寰佺殑閭ｄ釜鍧?            candidates.sort(key=lambda x: x['dist'])
            best = candidates[0]
            final_tx, final_ty = roi_x1 + best['center'][0], roi_y1 + best['center'][1]
            # 瑙嗚鍙嶉鍥炲～
            cv2.drawMarker(debug_img, best['center'], (0, 255, 0), cv2.MARKER_CROSS, 30, 3)
            print(f"[SKILL-V2] 璇箟鐗瑰緛鍚搁檮鎴愬姛: ({final_tx}, {final_ty})")
        
        # 淇濆瓨璇婃柇鍥?        debug_path = os.path.join(r"D:\Dev\autoplay\records", "semantic_debug.jpg")
        cv2.imwrite(debug_path, debug_img)
        
        if final_tx == -1:
            print("[SKILL-V2] 鏈兘璇嗗埆鍒版樉钁楃壒寰佸潡锛岄檷绾т娇鐢ㄧ墿鐞嗗亸绉汇€?)
            final_tx, final_ty = ax + 30, ay + 140 # 闄嶇骇鍥炵増鏈?1
        
        # 5. 鎵ц鐗╃悊鍘熻鐐瑰嚮
        config = self._load_config()
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        real_tx, real_ty = base_x + final_tx, base_y + final_ty
        
        for i in range(2):
            win32api.SetCursorPos((int(real_tx), int(real_ty)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)
            
        print(f"[SKILL-V2] 鎵ц瀹屾垚銆?)
        return True

    def _find_thumbnail_center(self, ax, ay, img):
        h, w, _ = img.shape
        roi = img[ay:min(ay+300, h), max(ax-100, 0):min(ax+300, w)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(cv2.GaussianBlur(gray, (3,3), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if 50 < rw < 200 and 50 < rh < 200:
                print(f"[SKILL] 鎺㈡祴鍒版綔鍦ㄧ缉鐣ュ浘鍖哄煙: {rw}x{rh}")
                return rx + max(ax-100, 0) + rw // 2, ry + ay + rh // 2
        return None, None

    def action_wait_visual(self, threshold=5.0, timeout=12):
        """鍘熷瓙绉湪锛氳瑙夊彉鍖栫瓑寰?(宸插鏁?"""
        config = self._load_config()
        if not config: return False
        raw = config["dock_rect"]
        monitor = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        print(f"[SKILL] 姝ｅ湪鐩戞祴鐢婚潰鍙樺寲 (闃堝€? {threshold}%, 瓒呮椂: {timeout}s)...")
        with mss.mss() as sct:
            base_frame = np.array(sct.grab(monitor))
            base_img = cv2.cvtColor(base_frame, cv2.COLOR_BGRA2GRAY)
            start_time = time.time()
            while time.time() - start_time < timeout:
                curr_img = cv2.cvtColor(np.array(sct.grab(monitor)), cv2.COLOR_BGRA2GRAY)
                diff = cv2.absdiff(base_img, curr_img)
                _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                roi_h, roi_w = int(base_img.shape[0] * 0.8), int(base_img.shape[1] * 0.8)
                y1, x1 = (base_img.shape[0] - roi_h)//2, (base_img.shape[1] - roi_w)//2
                roi_diff = diff_thresh[y1:y1+roi_h, x1:x1+roi_w]
                change_val = (cv2.countNonZero(roi_diff) / (roi_h * roi_w)) * 100
                if change_val > threshold: 
                    print(f"[SKILL] 妫€娴嬪埌鐢婚潰鍙樺寲瀹屾垚! ({change_val:.2f}%)")
                    return True
                time.sleep(0.5)
        print("[SKILL] 鐢婚潰鐩戞祴瓒呮椂锛屾湭鍙戠幇棰勬湡鍙樺寲銆?)
        return False

    def action_press_keys(self, keys=["down"], interval=0.5):
        """鍘熷瓙绉湪锛氭寜閿簭鍒楁敞鍏?(鐢?Agent 澶勭悊闅忔満闂撮殧)"""
        print(f"[SKILL] 娉ㄥ叆鎸夐敭: {keys}, 棰勮闂撮殧: {interval}")
        config = self._load_config()
        if config:
            data = config['dock_rect']
            cx, cy = data['x'] + data['width'] // 2, data['y'] + data['height'] // 2
            self.agent.double_click_at(cx, cy)
            time.sleep(0.5)
        self.agent.press_key_sequence(keys, interval=interval, hold_time=0.15)
        return True

    def action_zoom_pan_reset(self, landmark_keywords=["ref"], scroll_amount=15,
                               pan_dx=180, pan_dy=100, reset_by_double_click=True):
        """
        鍘熷瓙绉湪锛氭繁搴﹀贰鑸帶鍒?(鐗╃悊鍐呮牳纭寲鐗?
        """
        import win32gui, win32api, win32con
        print(f"\n[SKILL] 姝ｅ湪鎵ц Win32 鏆村姏宸¤埅: {landmark_keywords}")

        # --- Step 1: 鐗╃悊婵€娲讳笌瑙嗗浘鑷姩鍥炴 ---
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except: pass

        # 杈呭姪瀵逛綅锛氭墽琛屽墠鍙戦€佺墿鐞?LEFT锛岀‘淇濆湪 Response A
        # 琛ヤ竵锛氳繛鐐逛袱娆″苟澧炲姞鏃跺欢锛岀‘淇?UI 鐘舵€佹満鍦ㄨ繙绋嬫闈笂瀹屾垚鍒囨崲
        for _ in range(2):
            win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.2)
        time.sleep(0.8)

        # --- Step 1: 鎵惧埌鍦版爣浣嶇疆 ---
        view_path = self.action_screenshot("ref_search")
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)

        ax, ay = -1, -1
        # 棰勫姞杞藉閿欏叧閿瘝锛氶拡瀵瑰父瑙佺殑 OCR 璇杩涜闈欓粯澧炲己
        if any(k.lower() in ["response", "response a", "response b"] for k in landmark_keywords):
            landmark_keywords = list(set(landmark_keywords + ["rosponse", "respon", "rospon", "rosponse a", "rosponse b", "rbbponse", "rason", "roso"]))

        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in landmark_keywords):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    cur_ax, cur_ay = int(parts[0]), int(parts[1])
                    
                    # 鍏抽敭琛ヤ竵锛氬弻杞磋繃婊わ紝闃叉璇Е娴忚鍣?UI
                    if cur_ay < 160 or cur_ax < 20: 
                        print(f"[SKILL] 蹇界暐闈炲鐒﹀尯鍦版爣 (Anti-Interference): '{line}' at ({cur_ax}, {cur_ay})")
                        continue
                        
                    ax, ay = cur_ax, cur_ay
                    print(f"[SKILL] 鍛戒腑鐗╃悊宸¤埅閿氱偣: ({ax}, {ay})")
                    break
                except: continue

        if ay == -1:
            print(f"[SKILL] 璀﹀憡: 鏈兘鍙戠幇鍦版爣 {landmark_keywords}锛屽惎鐢ㄤ腑蹇冪偣瀵圭劍鍏滃簳銆?)
            config = self._load_config()
            ax, ay = config['dock_rect']['width'] // 2, config['dock_rect']['height'] // 2

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # --- 鏈€缁堢墿鐞嗗唴鏍告墽琛屽簭鍒?---
        actual_scroll = scroll_amount
        if isinstance(scroll_amount, str) and "-" in scroll_amount:
            try:
                min_s, max_s = map(int, scroll_amount.split("-"))
                actual_scroll = random.randint(min_s, max_s)
            except: pass
        elif isinstance(scroll_amount, list) and len(scroll_amount) == 2:
            try:
                actual_scroll = random.randint(int(scroll_amount[0]), int(scroll_amount[1]))
            except: pass

        target_x, target_y = int(base_x + ax), int(base_y + ay + 250)
        print(f"[SKILL] 鎵ц Win32 鐗╃悊瀵圭劍 ({target_x}, {target_y}) 涓庣缉鏀?x{actual_scroll}")
        
        for _ in range(3):
            win32api.SetCursorPos((target_x, target_y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)

        for _ in range(abs(actual_scroll)):
            # 鏍规嵁姝ｈ礋鍙峰喅瀹氭柟鍚?(120 涓哄悜涓?鏀惧ぇ, -120 涓哄悜涓?缂╁皬)
            direction = 120 if actual_scroll > 0 else -120
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, direction, 0)
            time.sleep(0.05)
        time.sleep(0.6)

        print(f"[SKILL] 鎵ц鐗╃悊娴佸钩绉? dx={pan_dx}, dy={pan_dy}")
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.3)
        steps = 15
        for i in range(steps):
            cx = target_x + (pan_dx * (i+1) // steps)
            cy = target_y + (pan_dy * (i+1) // steps)
            win32api.SetCursorPos((int(cx), int(cy)))
            time.sleep(0.04)
        time.sleep(0.3)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.8)

        if reset_by_double_click:
            print("[SKILL] 鎵ц鐗╃悊鍙屽嚮杩樺師")
            win32api.SetCursorPos((target_x, target_y))
            for _ in range(2):
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.05)

        return True

    def action_zoom(self, amount=5):
        """鍘熷瓙绉湪锛氱函绮圭殑鐗╃悊婊氳疆缂╂斁 (鏀寔闅忔満)"""
        actual_amount = amount
        if isinstance(amount, str) and "-" in amount:
            try:
                min_a, max_a = map(int, amount.split("-"))
                actual_amount = random.randint(min_a, max_a)
            except: pass
        elif isinstance(amount, list) and len(amount) == 2:
            try:
                actual_amount = random.randint(int(amount[0]), int(amount[1]))
            except: pass
            
        print(f"[SKILL] 鎵ц鐗╃悊缂╂斁: {actual_amount}")
        import win32api, win32con
        direction = 120 if actual_amount > 0 else -120
        for _ in range(abs(actual_amount)):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, direction, 0)
            time.sleep(0.05)
        return True

    def action_source_navigate_zoom_circle(self,
                                           source_keywords=["source"],
                                           response_keywords=["response a", "response", "rosponse a", "rosponse"],
                                           scroll_amount=4,
                                           circle_radius=70,
                                           circle_steps=24):
        """
        鍘熷瓙绉湪 - 绗?5 姝ュ畬鏁撮摼璺?
        1. 鐐瑰嚮 SOURCE 宸︿晶缂╃暐鍥?        2. 鎸変笅鍚戜笅鏂瑰悜閿Е鍙戝鑸?        3. 绛夊緟鍙充晶 Response A 澶у浘鍑虹幇
        4. 鐐瑰嚮璇ュぇ鍥?        5. 婊氳疆 Zoom In
        6. 鎸変綇宸﹂敭缁曞渾鍦?PAN
        7. 鍙屽嚮杩樺師
        """
        import pydirectinput
        import win32api, win32con, math

        print(f"\n[SKILL] 鎵ц Source->Down->ResponseA->Zoom->Circle->Reset")

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # Step 1: OCR 鎵?SOURCE 鍦版爣
        view_path = self.action_screenshot("source_nav")
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)
        src_x, src_y = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in source_keywords):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    src_x, src_y = int(parts[0]), int(parts[1])
                    break
                except: continue

        if src_y == -1:
            print("[SKILL] 鏈壘鍒?SOURCE锛岀粓姝€?)
            return False

        # 鐐瑰嚮 SOURCE 涓嬫柟灏忓浘鏍?        self.agent.click_at(base_x + src_x, base_y + src_y + 80)
        time.sleep(0.5)

        # Step 2: 鎸変笅鏂瑰悜閿?        pydirectinput.keyDown('down'); time.sleep(0.15); pydirectinput.keyUp('down')
        time.sleep(1.0)

        # Step 3: 绛夊緟 Response A 鍑虹幇 (宸插鏁?
        self.action_wait_visual(threshold=5.0, timeout=8)

        # Step 4: 閲嶆柊鎴浘鎵?Response A 澶у浘
        img2 = cv2.imread(self.action_screenshot("response_a"))
        context2 = self.ocr.read_screen(img2)
        resp_x, resp_y = -1, -1
        for line in context2.split('\n'):
            if any(k.lower() in line.lower() for k in response_keywords):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    resp_x, resp_y = int(parts[0]), int(parts[1])
                    break
                except: continue

        if resp_y == -1:
            print("[SKILL] 鏈壘鍒?Response A锛岀粓姝€?)
            return False

        # Response A 鏂囧瓧鍙充晶澶у浘锛?鍋忕Щ锛?        img_x = base_x + resp_x + 150
        img_y = base_y + resp_y + 60
        self.agent.click_at(img_x, img_y)
        time.sleep(0.4)

        # Step 5: 婊氳疆 Zoom In
        pydirectinput.moveTo(img_x, img_y)
        for _ in range(scroll_amount):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
            time.sleep(0.15)
        time.sleep(0.5)

        # Step 6: 鍦嗗湀 PAN
        pydirectinput.moveTo(img_x + circle_radius, img_y)
        pydirectinput.mouseDown(button='left')
        time.sleep(0.1)
        for step in range(circle_steps + 1):
            angle = 2 * math.pi * step / circle_steps
            pydirectinput.moveTo(
                img_x + int(circle_radius * math.cos(angle)),
                img_y + int(circle_radius * math.sin(angle))
            )
            time.sleep(0.04)
        pydirectinput.mouseUp(button='left')
        time.sleep(0.5)

        # Step 7: 鍙屽嚮杩樺師
        pydirectinput.doubleClick(img_x, img_y)
        time.sleep(0.3)
        print("[SKILL] Source->Navigate->Zoom->Circle->Reset 瀹屾垚銆?)
        return True

    def action_output_navigate_zoom_circle_reverse(self,
                                                    output_keywords=["output"],
                                                    response_keywords=["response b", "response", "rosponse b", "rosponse"],
                                                    zoom_in_big=6,
                                                    zoom_out=4,
                                                    zoom_in_small=2,
                                                    circle_radius=100,
                                                    circle_steps=30):
        """
        鍘熷瓙绉湪 - 绗?6 姝ュ畬鏁撮摼璺紙鍙嶅悜澶у渾鍦堢増锛?
        1. 鐐瑰嚮 OUTPUT 涓嬫柟宸︿晶灏忓浘鏍?        2. 鎸変笅鍚戝彸鏂瑰悜閿?        3. 绛夊緟 Response B 鍑虹幇
        4. 鐐瑰嚮 Response B 澶у浘
        5. Zoom In 澶у箙鏀惧ぇ
        6. Zoom Out 缂╁洖
        7. Zoom In 寰皟鏀惧ぇ
        8. 鍙嶆柟鍚戝ぇ鍦嗗湀 PAN锛堥€嗘椂閽堬級
        9. 鍙屽嚮杩樺師
        """
        import pydirectinput
        import win32api, win32con, math

        print(f"\n[SKILL] 鎵ц Output->Right->ResponseB->ZoomInOut->ReversePAN->Reset")

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # Step 1: OCR 鎵?OUTPUT 鍦版爣
        img = cv2.imread(self.action_screenshot("output_nav"))
        context = self.ocr.read_screen(img)
        out_x, out_y = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in output_keywords):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    out_x, out_y = int(parts[0]), int(parts[1])
                    print(f"[DEBUG] 鎵惧埌 OUTPUT 鏂囧瓧鍧愭爣: ({out_x}, {out_y})")
                    break
                except: continue

        if out_y == -1:
            print("[SKILL] 鏈壘鍒?OUTPUT锛岀粓姝€?)
            return False

        # 璁＄畻鍥炬爣鐗╃悊鍧愭爣锛氶€氬父鍥炬爣鍦ㄦ枃瀛椾笅鏂癸紝宸︿晶鍥炬爣绋嶅井鍋忓乏
        target_icon_x = base_x + out_x - 40 
        target_icon_y = base_y + out_y + 90
        
        # --- 澧炲己瑙嗚琛ㄧ幇锛氬厛绉诲姩鍒颁綅缃?---
        print(f"[SKILL] 姝ｅ湪绉诲姩鍒?OUTPUT 鍥炬爣: ({target_icon_x}, {target_icon_y})")
        pydirectinput.moveTo(target_icon_x, target_icon_y, duration=0.5) 
        time.sleep(0.3)
        
        # 婵€娲荤獥鍙ｇ‘淇濇寜閿湁鏁?        self.agent.activate_window(self.agent.profile_name) 
        
        # 纭垏鐐瑰嚮
        self.agent.click_at(target_icon_x, target_icon_y)
        time.sleep(0.5)

        # Step 2: 鎸夊彸鏂瑰悜閿?        print("[SKILL] 鍙戦€?RIGHT 鏂瑰悜閿帶鍒?..")
        pydirectinput.press('right')
        
        # --- Step 3: 鏋佽嚧椴佹绛夊緟 Response B (妯＄硦鍖归厤 + 鎸夐敭閲嶈瘯) ---
        print("[SKILL] 姝ｅ湪绛夊緟鍙充晶 Response B 鍔犺浇...")
        wait_start = time.time()
        resp_x, resp_y = -1, -1
        has_retried_key = False
        
        while time.time() - wait_start < 15: # 寤堕暱鍒?5绉?            view_path = self.action_screenshot("polling_resp_b")
            img2 = cv2.imread(view_path)
            context2 = self.ocr.read_screen(img2)
            
            for line in context2.split('\n'):
                l_line = line.lower()
                # 妯＄硦鍖归厤锛氬彧瑕佹湁 response 涓斿湪鍙冲崐鍖?(base_x+300浠ュ彸)
                if "response" in l_line and "response a" not in l_line:
                    try:
                        parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                        cur_x, cur_y = int(parts[0]), int(parts[1])
                        
                        # 浣嶇疆鏍￠獙锛歊esponse B 蹇呭湪鍙充晶
                        if cur_x > 350: 
                            resp_x, resp_y = cur_x, cur_y
                            print(f"[SKILL] 妯＄硦鍖归厤閿佸畾鍙充晶鐩爣: {line}")
                            break
                    except: continue
            
            if resp_x != -1: break
            
            # 琛ヤ竵锛氬鏋滅瓑寰呰秴杩?4 绉掕繕娌″姩闈欙紝鍙兘鏄寜閿涪浜嗭紝閲嶆寜涓€娆?            if (time.time() - wait_start) > 4.0 and not has_retried_key:
                print("[SKILL] 椤甸潰鏈搷搴旓紝灏濊瘯閲嶆寜 RIGHT 閿?..")
                pydirectinput.press('right')
                has_retried_key = True

            print(f"[SKILL] 鎼滅储涓?.. (宸茬瓑 {int(time.time()-wait_start)}s)")
            time.sleep(1.2)

        if resp_x == -1:
            print("[SKILL] 涓ラ噸璀﹀憡: 15绉掑唴鏈兘鍦ㄥ彸渚ч攣瀹氱洰鏍囥€?)
            return False

        # --- Step 4: 娓叉煋缂撳啿 (缁欏ぇ鍥剧墖 2.0 绉掑姞杞芥椂闂? ---
        print("[SKILL] 鐩爣宸查攣瀹氾紝姝ｅ湪绛夊緟楂樻竻澶у浘绋冲畾娓叉煋...")
        time.sleep(2.0)

        # 鏈€缁堢‘瀹氬ぇ鍥句腑蹇冨潗鏍?(Response B 鏂囧瓧鍙充晶)
        img_x = base_x + resp_x + 150
        img_y = base_y + resp_y + 60
        
        print(f"[SKILL] 娓叉煋灏辩华锛屽噯澶囧紑濮嬪彉閫熺缉鏀句氦浜?..")
        self.agent.click_at(img_x, img_y)
        time.sleep(0.4)
        pydirectinput.moveTo(img_x, img_y)

        def scroll(amount, direction=1):
            for _ in range(abs(amount)):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120 * direction, 0)
                time.sleep(0.15)

        # Step 5: 澶у箙 Zoom In
        print(f"[SKILL] Zoom In 澶?x{zoom_in_big}")
        scroll(zoom_in_big, 1)
        time.sleep(0.4)

        # Step 6: Zoom Out
        print(f"[SKILL] Zoom Out x{zoom_out}")
        scroll(zoom_out, -1)
        time.sleep(0.4)

        # Step 7: 寰箙 Zoom In
        print(f"[SKILL] Zoom In 灏?x{zoom_in_small}")
        scroll(zoom_in_small, 1)
        time.sleep(0.5)

        # Step 8: 鍙嶆柟鍚戝ぇ鍦嗗湀 PAN锛堥€嗘椂閽堬紝angle 閫掑噺锛?        print(f"[SKILL] 閫嗘椂閽堝ぇ鍦嗗湀 PAN (R={circle_radius})")
        pydirectinput.moveTo(img_x + circle_radius, img_y)
        pydirectinput.mouseDown(button='left')
        time.sleep(0.1)
        for step in range(circle_steps + 1):
            angle = -2 * math.pi * step / circle_steps  # 璐熷彿 = 閫嗘椂閽?            pydirectinput.moveTo(
                img_x + int(circle_radius * math.cos(angle)),
                img_y + int(circle_radius * math.sin(angle))
            )
            time.sleep(0.04)
        pydirectinput.mouseUp(button='left')
        time.sleep(0.5)

        # Step 9: 鍙屽嚮杩樺師
        pydirectinput.doubleClick(img_x, img_y)
        time.sleep(0.3)
        print("[SKILL] Output->Right->ResponseB->Zoom->ReversePAN->Reset 瀹屾垚銆?)
        return True

    def action_scroll_home_end(self, direction="end"):
        """鍘熷瓙绉湪锛氭渶楂樼瓑绾х墿鐞嗘粴鍔?(鍐呭鍖哄鐒︾増)"""
        import pydirectinput
        print(f"[SKILL] 姝ｅ湪鍚姩鍐呭鍖哄己鍔涙粴鍔? {direction}")
        
        self.agent.activate_window(self.agent.profile_name)
        time.sleep(0.3)
        
        config = self._load_config()
        if not config: return False
        
        # 鏍稿績鏀硅繘锛氬鎵惧唴瀹瑰尯鐨勬爣蹇楁€у湴鏍囨枃瀛楄繘琛屽鐒︾偣鍑伙紝纭繚婊氬姩閽堝鍐呭绐楁牸
        # 閽堝 4K 绔栧睆鎵╁厖鍏抽敭璇嶉浄杈? 鍔犲叆 Elo, Guidelines, Mango 绛?        view_path = self.action_screenshot("scroll_focus")
        img = cv2.imread(view_path)
        if img is None: return False
        
        context = self.ocr.read_screen(img)
        
        focus_x, focus_y = -1, -1
        target_kws = ["inputs", "omni", "source", "response", "tina", "elo", "guidelines", "mango", "multimango"]
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in target_kws):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    ax, ay = int(parts[0]), int(parts[1])
                    
                    # 鍏抽敭琛ヤ竵锛氬弻杞村潗鏍囪繃婊?(绮句慨鐗?
                    # 1. 蹇界暐绐楀彛椤堕儴 160 鍍忕礌鍐呯殑鍦版爣锛堜粎閬尅鏍囩鏍?鍦板潃鏍?涔︾鏍忥級
                    # 2. 蹇界暐鏋佺獎渚ц竟 20 鍍忕礌鍐呯殑鍦版爣锛堝熀鏈槻璇Е锛?                    if ay < 160 or ax < 20:
                        print(f"[SKILL] 蹇界暐闈炲唴瀹瑰尯鍦版爣 (System UI Buffer): '{line}' at ({ax}, {ay})")
                        continue
                        
                    focus_x = config['dock_rect']['x'] + ax
                    focus_y = config['dock_rect']['y'] + ay
                    print(f"[SKILL] 鍛戒腑銆愪换鍔℃牳蹇冨尯銆戝湴鏍?'{line}'锛屾墽琛岀偣鍑诲鐒?..")
                    break
                except: continue
                
        if focus_x == -1:
            # 闄嶇骇鏂规锛氱偣鍑荤洰鏍囩獥鍙ｅ乏渚?1/4 澶勶紝纭繚閬垮紑涓棿绌虹獥鍖?            print("[SKILL] 鏈彂鐜板湴鏍囨枃妗堬紝鍚姩鍖哄煙绾犲亸瀵圭劍 (Region-Based)...")
            focus_x = config['dock_rect']['x'] + (config['dock_rect']['width'] // 4)
            focus_y = config['dock_rect']['y'] + (config['dock_rect']['height'] // 3)
            
        # 鍏ㄩ摼璺姞鍥猴細寮哄埗鐗╃悊鐒︾偣閿佸畾
        import win32gui
        import win32api
        import win32con
        
        # 1. 寮哄姏婵€娲荤洰鏍囩獥鍙?(Window-Level Focus)
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            print(f"[SKILL] 姝ｅ湪寮哄埗缃《鐩爣绐楀彛 [HWND:{hwnd}]...")
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except Exception as e:
                print(f"[SKILL] 绐楀彛缃《鎻愮ず: {e}")

        # 鎵ц涓夎繛鍑荤‘淇濇縺娲诲鍣?(鏀圭敤搴曞眰 win32api 缁曡繃 pydirectinput 鐨勮繙绋嬬幆澧冨崱椤?
        for i in range(3):
            print(f"[SKILL] 姝ｅ湪鎵ц搴曞眰瀵圭劍鐐瑰嚮 {i+1}/3 (鐗╃悊鍧愭爣: {focus_x}, {focus_y})...")
            win32api.SetCursorPos((int(focus_x), int(focus_y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.15)
        
        is_end = direction.lower() == 'end'
        # VK_NEXT (PageDown) = 0x22, VK_PRIOR (PageUp) = 0x21
        vk_code = 0x22 if is_end else 0x21
        main_key_name = 'PageDown' if is_end else 'PageUp'
        burst_count = 15 if is_end else 12 
            
        print(f"[SKILL] 婵€娲诲畬鎴愶紝绔嬪嵆閫氳繃 Win32 娉ㄥ叆 {main_key_name} x{burst_count} 鐗╃悊杩炲彂...")
        for i in range(burst_count):
            # 妯℃嫙鎸変笅鍜屾姮璧?(澧炲姞鎸変笅鏃堕暱锛岀‘淇濊繙绋嬬幆澧冩崟鑾?
            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.03) # 澧炲姞鎸変綇鏃堕棿 (Hold time)
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            if i % 5 == 0: print(f"[SKILL] 婊氬姩杩涘害: {i}/{burst_count}...")
            time.sleep(0.08) # 澧炲姞闂撮殧鏃堕棿 (Inter-key delay)
            
        # 婊氳疆闀挎晥琛ヤ竵
        print(f"[SKILL] 姝ｅ湪娉ㄥ叆纭欢绾ф粴杞ˉ涓?..")
        for _ in range(12):
            amount = -1200 if is_end else 1200
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            time.sleep(0.06)
            
        print(f"[SKILL] 鍐呭鍖哄叏閾捐矾鏆村姏婊氬姩宸插畬鎴?)
        time.sleep(0.8) 
        return True

    def action_close_tab(self):
        """鍘熷瓙绉湪锛氬叧闂綋鍓嶆祻瑙堝櫒鏍囩椤?(Ctrl+W)"""
        import pydirectinput
        self.agent.activate_window(self.agent.profile_name)
        time.sleep(0.3)
        print("[SKILL] 姝ｅ湪鍏抽棴褰撳墠鏍囩椤?(Ctrl+W)...")
        pydirectinput.keyDown('ctrl')
        pydirectinput.press('w')
        pydirectinput.keyUp('ctrl')
        time.sleep(0.5)
        return True

    def action_click_raw(self, rel_x, rel_y):
        """
        鍘熷瓙绉湪锛氱浉瀵圭墿鐞嗙偣鍑?(褰曞埗鍣ㄥ洖閫€鏂规)
        鍩轰簬瀵逛綅鍩哄噯鐨勫亸绉荤偣鍑伙紝纭繚绐楀彛绉诲姩鍚庝緷鐒舵湁鏁堛€?        """
        import win32api, win32con, win32gui
        config = self._load_config()
        if not config: return False
        
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        abs_x, abs_y = base_x + rel_x, base_y + rel_y
        
        print(f"[SKILL] 鎵ц鐗╃悊鐐瑰嚮: ({abs_x}, {abs_y}) [Rel: {rel_x}, {rel_y}]")
        
        # 寮哄埗婵€娲荤獥鍙ｇ‘淇濈偣鍑绘湁鏁?        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except: pass

        for _ in range(2):
            win32api.SetCursorPos((int(abs_x), int(abs_y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)
        
        time.sleep(0.5)
        return True

    def action_sleep(self, seconds=3.0):
        """鍘熷瓙绉湪锛氭敮鎸佸浐瀹氭垨闅忔満寤舵椂绛夊緟 (V27.5)"""
        final_seconds = seconds
        if isinstance(seconds, str) and "-" in seconds:
            try:
                min_s, max_s = map(float, seconds.split("-"))
                final_seconds = random.uniform(min_s, max_s)
            except: pass
        elif isinstance(seconds, list) and len(seconds) == 2:
            try:
                final_seconds = random.uniform(float(seconds[0]), float(seconds[1]))
            except: pass
            
        print(f"[SKILL] 寤舵椂绛夊緟 {final_seconds:.2f} 绉?..")
        time.sleep(final_seconds)
        return True
