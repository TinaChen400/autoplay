import sys
import json
import os
import cv2
import time
import numpy as np
import mss

sys.path.append(r"D:/Dev/autoplay")
from src.utils.vision import VisionCapture
from src.utils.ocr_reader import OCRReader
from src.execution.remote_agent import RemoteAgent

class MSISkills:
    def __init__(self):
        self.agent = RemoteAgent(profile_name="MSI")
        self.vc = VisionCapture()
        self.ocr = OCRReader()
        self.records_dir = r"D:/Dev/autoplay/records"
        self.db_path = r"D:/Dev/autoplay/config/calibration_db.json"

    def _load_config(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    return json.load(f)
            except: pass
        return None

    def capture_standard_view(self):
        """绾跨▼瀹夊叏鐨勫崟娆℃姄鎷?""
        config = self._load_config()
        dock_rect = None
        if config:
            raw = config.get("dock_rect")
            dock_rect = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        # 姣忔璋冪敤閮藉垱寤虹嫭绔嬬殑 mss 瀹炰緥锛屽交搴曡閬跨嚎绋嬪睘鎬ч敊璇?        with mss.mss() as sct:
            screenshot = sct.grab(dock_rect) if dock_rect else sct.grab(sct.monitors[1])
            save_path = os.path.join(self.records_dir, "skill_msi_last_view.jpg")
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
            return save_path

    def find_thumbnail_rect(self, anchor_x, anchor_y, img):
        h, w, _ = img.shape
        roi_top, roi_bottom = anchor_y, min(anchor_y + 300, h)
        roi_left, roi_right = max(anchor_x - 100, 0), min(anchor_x + 300, w)
        
        roi_img = img[roi_top:roi_bottom, roi_left:roi_right]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if 50 < rw < 200 and 50 < rh < 200:
                return rx + roi_left + rw // 2, ry + roi_top + rh // 2
        return None, None

    def click_input_thumbnail(self):
        print("\n--- 鎵ц鎶€鑳? click_input_thumbnail ---")
        view_path = self.capture_standard_view()
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)
        anchor_x, anchor_y = -1, -1
        keywords = ["inputs", "input", "source", "output"]
        
        for line in context.split('\n'):
            if any(k in line.lower() for k in keywords):
                try:
                    parts = line.split("鍧愭爣: (")[1].split(")")[0].split(",")
                    anchor_x, anchor_y = int(parts[0]), int(parts[1])
                    break
                except: continue
        
        if anchor_y == -1: return False
        target_x, target_y = self.find_thumbnail_rect(anchor_x, anchor_y, img)
        config = self._load_config()
        if not config: return False
        
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        tx, ty = (base_x + target_x, base_y + target_y) if target_x else (base_x + anchor_x, base_y + anchor_y + 120)
        self.agent.click_at(tx, ty)
        return True

    def wait_for_visual_change(self, timeout=10, threshold=15.0):
        config = self._load_config()
        if not config: return False
        raw = config["dock_rect"]
        monitor = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
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
                if (cv2.countNonZero(roi_diff) / (roi_h * roi_w)) * 100 > threshold: return True
                time.sleep(0.5)
        return False

    def interact_with_large_image(self):
        if not self.wait_for_visual_change(): return False
        config = self._load_config()
        if not config: return False
        data = config['dock_rect']
        cx, cy = data['x'] + data['width'] // 2, data['y'] + data['height'] // 2
        self.agent.double_click_at(cx, cy) 
        time.sleep(1.0)
        self.agent.press_key_sequence(['down', 'right', 'left', 'up'], interval=0.5, hold_time=0.15)
        return True

if __name__ == "__main__":
    skills = MSISkills()
    if not skills.click_input_thumbnail(): skills.interact_with_large_image()

    def action_content_scroll(self, direction="end"):
        """内容区强力滚动 (home/end)"""
        import win32api, win32con, win32gui
        import pydirectinput
        import time
        
        is_end = (direction == "end")
        print(f"[SKILL] 正在启动内容区强力滚动: {direction}")
        self.agent.activate_window("Tina")
        time.sleep(0.3)
        
        config = self._load_config()
        if not config:
            return False
            
        base_x = config["dock_rect"]["x"] + config["dock_rect"]["width"] // 2
        base_y = config["dock_rect"]["y"] + config["dock_rect"]["height"] // 2
        
        # 截图并用 OCR 找内容区地标
        view_path = self.action_screenshot("scroll_focus")
        img = __import__("cv2").imread(view_path)
        results = self.ocr.reader.readtext(img) if img is not None else []
        
        system_ui_buffer = ["tina", "multimango", "omni", "comtask", "task"]
        content_keywords = ["rate", "response", "overall", "instruction", "id preservation",
                           "content", "visual", "generated", "submit", "comparison", "omni elo", "omni"]
        
        click_x, click_y = base_x, base_y
        for res in results:
            text = res[1].lower()
            cx = (res[0][0][0] + res[0][1][0]) / 2
            cy = (res[0][0][1] + res[0][2][1]) / 2
            
            if any(s in text for s in system_ui_buffer):
                print(f"[SKILL] 忽略非内容区地标 (System UI Buffer): '文本: '{res[1]}' | 坐标: ({int(cx)}, {int(cy)})'  at ({int(cx)}, {int(cy)})")
                continue
                
            if any(k in text for k in content_keywords):
                abs_x = base_x + cx - config["dock_rect"]["width"] // 2 + config["dock_rect"]["x"]
                abs_y = base_y + cy - config["dock_rect"]["height"] // 2 + config["dock_rect"]["y"]
                print(f"[SKILL] 命中【任务核心区】地标 '文本: '{res[1]}' | 坐标: ({int(cx)}, {int(cy)})'，执行点击对焦...")
                
                hwnd = win32gui.FindWindow(None, "Tina")
                if hwnd:
                    print(f"[SKILL] 正在强制置顶目标窗口 [HWND:{hwnd}]...")
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.3)
                    except: pass
                
                for attempt in range(3):
                    print(f"[SKILL] 正在执行底层对焦点击 {attempt+1}/3 (物理坐标: {int(abs_x)}, {int(abs_y)})...")
                    win32api.SetCursorPos((int(abs_x), int(abs_y)))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    time.sleep(0.1)
                click_x, click_y = int(abs_x), int(abs_y)
                break
        
        key = "End" if is_end else "Home"
        count = 15 if is_end else 12
        print(f"[SKILL] 激活完成，立即通过 Win32 注入 {'PageDown' if is_end else 'PageUp'} x{count} 物理连发...")
        
        for i in range(count):
            if i % 5 == 0:
                print(f"[SKILL] 滚动进度: {i}/{count}...")
            pydirectinput.press("pagedown" if is_end else "pageup")
            time.sleep(0.08)
        
        print(f"[SKILL] 正在注入硬件级滚轮补丁...")
        for _ in range(12):
            amount = -1200 if is_end else 1200
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            time.sleep(0.06)
            
        print(f"[SKILL] 内容区全链路暴力滚动已完成")
        time.sleep(0.8) 
        return True

    def action_llm_scoring_table(self):
        """[V33.7] 分段填表:先填顶部 Overall/Instruction，再填底部其余维度"""
        import time, re, cv2, random, os
        import numpy as np
        import pyautogui
        
        print(f"\n[SKILL-V33.7] >>> 启动全自动分段填表流程 <<<")
        
        # 0. 去豆包拿答案 (强制验身版)
        print("  - [Oracle] 正在切换至浏览器提取数据...")
        if self.oracle.action_focus_gpt_window(verify_content=True):
            print("  - [Oracle] 验身成功，数据已就绪。")
        else:
            print("  - [Warn] 未能验身，将尝试直接使用当前剪贴板...")
            
        ai_response = self.oracle.action_get_response()
        if not ai_response or "Overall" not in ai_response:
            print(f"  - [Error] 捕获内容无效！前40字: {str(ai_response)[:40]}")
            return False

        # 解析决策数据
        print(f"  - [Parser] 正在解析 AI 响应...")
        decision_map = {}
        dim_keywords = {
            "Overall": ["overall", "总评", "总体", "preference"],
            "Instruction": ["instruction", "指令", "遵循", "following"],
            "Id": ["id preservation", "id", "五官"],
            "Content": ["content preservation", "content", "内容"],
            "Visual": ["visual", "画质", "视觉", "quality"],
            "Generated": ["generated", "less ai", "人工痕迹", "ai generated"]
        }
        for line in ai_response.split('\n'):
            m = re.search(r"([\u4e00-\u9fa5\w\s]+)[::\s]+([A-Z\s/]+)(?:[\||｜]\s*理由[::\s]*(.*))?", line, re.IGNORECASE)
            if m:
                raw_dim, val = m.group(1).strip().lower(), m.group(2).strip().upper()
                reason = m.group(3).strip() if m.group(3) else "N/A"
                for std_name, kws in dim_keywords.items():
                    if any(kw in raw_dim for kw in kws):
                        decision_map[std_name] = (val, reason); break

        # 补充扫射
        if len(decision_map) < 3:
            all_pairs = re.findall(r"([\u4e00-\u9fa5\w\s]+)[::\s]+(A|B|Both Good|Both Bad|Tie|N/A)", ai_response, re.IGNORECASE)
            for raw_dim, val in all_pairs:
                raw_dim = raw_dim.strip().lower()
                for std_name, kws in dim_keywords.items():
                    if any(kw in raw_dim for kw in kws):
                        if std_name not in decision_map: decision_map[std_name] = (val.strip().upper(), "N/A"); break

        if not decision_map:
            print(f"  - [Error] 解析失败，原始文本前60字: {ai_response[:60]}")
            return False
        
        print(f"  - [Parser] 解析完成: {list(decision_map.keys())}")

        # 分段执行点击
        self.agent.activate_window("Tina")
        
        # Phase 1: 顶部 (Overall + Instruction)
        print("  - [Phase 1] 正在填入顶部维度...")
        self.action_content_scroll("home")
        time.sleep(1.2)
        self._process_scoring_segment(decision_map, ["Overall", "Instruction"])
        
        # Phase 2: 底部 (其余维度)
        print("  - [Phase 2] 正在填入底部维度...")
        self.action_content_scroll("end")
        time.sleep(1.2)
        self._process_scoring_segment(decision_map, ["Visual", "Content", "Generated", "Id", "ID"])
        
        print("[SKILL] V33.7 分段填表完成！")
        return True

    def _process_scoring_segment(self, decision_map, filter_dims):
        """视觉对位引擎:识别并点击当前屏幕内的指定维度"""
        import cv2, time, random
        view_path = self.action_screenshot("scoring_segment")
        img = cv2.imread(view_path)
        if img is None: return
        
        config = self._load_config()
        base_x, base_y = config["dock_rect"]["x"], config["dock_rect"]["y"]
        results = self.ocr.reader.readtext(img)
        
        for dim_key in filter_dims:
            if dim_key not in decision_map: continue
            val, reason = decision_map[dim_key]
            
            dim_y = -1
            for res in results:
                if dim_key.lower() in res[1].lower():
                    dim_y = (res[0][0][1] + res[0][2][1]) / 2
                    print(f"    [Align] 找到维度 '{dim_key}' at Y={dim_y}")
                    break
            
            if dim_y == -1:
                print(f"    [Warn] 本屏未找到: {dim_key}")
                continue
            
            for res in results:
                text = res[1].upper()
                btn_y = (res[0][0][1] + res[0][2][1]) / 2
                if abs(btn_y - dim_y) < 80:
                    is_match = False
                    if val == "RESPONSE A" and ("RESP" in text and "A" in text): is_match = True
                    elif val == "RESPONSE B" and ("RESP" in text and "B" in text): is_match = True
                    elif val in text or text in val: is_match = True
                    
                    if is_match:
                        btn_x = (res[0][0][0] + res[0][1][0]) / 2
                        print(f"    [Click] '{dim_key}' -> '{val}': ({base_x + btn_x:.0f}, {base_y + btn_y:.0f})")
                        self.agent.click_at(base_x + btn_x, base_y + btn_y)
                        time.sleep(random.uniform(0.4, 0.6))
                        break

    def action_llm_ultimate_flow(self, expert_profile="portrait_v4k"):
        """[V31.0] 全自动视觉抓取与专家研判主流程"""
        import time
        print(f"\n[SKILL-V31.0] 启动极简研判流程 (仅 2 张图)...")
        
        self.oracle.action_clear_queue()
        
        # 1/2 抓取页面顶部
        print("  - [1/2] 抓取页面顶部 (Prompt)...")
        self.action_content_scroll("home")
        config = self._load_config()
        if config:
            self.oracle.action_add_to_queue(config["dock_rect"])
        
        # 2/2 抓取页面底部
        print("  - [2/2] 抓取页面底部 (Form)...")
        self.action_content_scroll("end")
        if config:
            self.oracle.action_add_to_queue(config["dock_rect"])
        
        # 构建专家提示词
        expert_prompt = self.oracle.system_prompt
        if hasattr(self, 'em') and self.em:
            try:
                expert_profile_data = self.em.get_profile(expert_profile)
                prompt_ext = self.em.generate_prompt_extension(expert_profile_data)
                protocol = (
                    "请对附件 2 张截图进行专业对比分析，提取评分数据。你的回答【必须】严格遵循以下协议:\n\n"
                    "### 输出协议 ###\n"
                    "1. 格式:[维度名]: [选项] | 理由: [对比分析]\n"
                    "2. 选项必须从以下集合中选择: A, B, Tie, Both Good, Both Bad, N/A\n"
                    "3. 理由要求:Overall 需 100 字节左右深度分析；子维度需 20 字节左右对比证据。\n"
                    "4. 禁止画图，禁止开场白，直接输出数据。\n\n"
                    "### 待提取项 ###\n"
                    "Overall: [选项] | 理由: [理由]\n"
                    "Instruction: [选项] | 理由: [理由]\n"
                    "ID: [选项] | 理由: [理由]\n"
                    "Content: [选项] | 理由: [理由]\n"
                    "Visual: [选项] | 理由: [理由]\n"
                    "Generated: [选项] | 理由: [理由]\n\n"
                    "--------------------------------------------------\n"
                    "专家研判准则:\n"
                )
                expert_prompt = protocol + prompt_ext
            except: pass
        
        # 投喂给豆包
        return self.oracle.action_send_queue_to_gpt(expert_prompt)
