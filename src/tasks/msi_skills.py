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
    MSI 原子技能积木库 (V27: LLM Integrated)
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
        步骤 1: 投喂截图与指令至豆包/GPT (V28.3)
        """
        if prompt is None:
            # 使用默认提示词
            prompt = self.oracle.system_prompt
            
        print("[SKILL] 正在投喂 UI 截图与指令至豆包/GPT...")
        
        # 1. 物理位置准备 (加载当前 Tina 坐标)
        config = self._load_config()
        if not config or "dock_rect" not in config:
            print("[SKILL] 错误: 未校准 Dock 坐标，无法截图")
            return False
            
        dock_rect = config["dock_rect"]
        
        # 2. 截图并存入剪贴板
        if not self.oracle.action_capture_to_clipboard(dock_rect):
            return False
            
        # 3. 唤起浏览器并发送
        if not self.oracle.action_focus_gpt_window():
            return False
            
        if not self.oracle.action_send_to_gpt(prompt):
            return False
        return True

    def action_llm_extract_click(self):
        """
        步骤 2: 抓取 LLM 结果并执行点击 (V28.1 优化版)
        """
        print("[SKILL] 启动视觉提取引擎...")
        decision = self.oracle.action_extract_decision(self.ocr)
        
        # 立即反馈至 UI
        if self.bridge:
            for step in self.bridge.steps:
                if step.methodName == "action_llm_extract_click":
                    step.result_data = f"{decision}" if decision else "识别失败"
                    break
            
            # 强制通知 UI 刷新
            if hasattr(self.bridge, 'on_step_added_cb') and self.bridge.on_step_added_cb: 
                self.bridge.on_step_added_cb()

        if not decision:
            print("[SKILL] LLM 未能给出有效决策")
        # 这里的决策 A/B 需要映射到 action_click_smart 的关键字
        keyword = f"Response {decision}"
        print(f"[SKILL] GPT 最终决策: {decision} -> 尝试点击 '{keyword}'")
        
        # 自动切换回 Tina 窗口 (通过 WindowManager)
        hwnd = win32gui.FindWindow(None, "Tina")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            
        return self.action_click_smart(keywords=[keyword])

    def _save_dock_rect(self, x, y, w, h):
        """由 UI 实时调用的同步接口，更新物理对位基准"""
        dock_rect = {"x": x, "y": y, "width": w, "height": h}
        # 直接通过硬件管理器保存，确保全局一致性
        self.hw.update_calibration(dock_rect=dock_rect)

    def _load_config(self):
        """从活跃环境档案加载基准参数"""
        return self.hw.get_active_calibration()

    def action_screenshot(self, label="view"):
        """原子积木：拍摄物理对位快照（V14.5 高分屏兼容版）"""
        config = self._load_config()
        dock_rect = None
        if config:
            raw = config.get("dock_rect")
            # 补丁：确保坐标为整数且在合规范围内
            dock_rect = {
                "left": int(raw["x"]), 
                "top": int(raw["y"]), 
                "width": int(raw["width"]), 
                "height": int(raw["height"])
            }
        
        with mss.mss() as sct:
            # 高分屏补丁：直接抓取指定的物理坐标矩形，不针对单个 monitor 索引
            try:
                screenshot = sct.grab(dock_rect) if dock_rect else sct.grab(sct.monitors[0])
                save_path = os.path.join(self.records_dir, f"snap_{label}.jpg")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
                print(f"[SKILL] 快照保存: {save_path} (Region: {dock_rect})")
                return save_path
            except Exception as e:
                print(f"[SKILL] 截图失败，回切模式: {e}")
                screenshot = sct.grab(sct.monitors[0])
                save_path = os.path.join(self.records_dir, f"snap_{label}_fallback.jpg")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
                return save_path

    def action_click_landmark(self, keywords=["inputs", "input"], offset_y=140, optional=False):
        """原子积木：地标定位与点击 (Tina 增强版，支持 optional 模式)"""
        print(f"[SKILL] 开始地标定位，关键词: {keywords} (Optional: {optional})")
        
        # 补丁：点击前强制激活窗口，确保点击下发有效
        self.agent.activate_window(self.agent.profile_name)
        time.sleep(0.5)
        
        view_path = self.action_screenshot("landmark_search")
        img = cv2.imread(view_path)
        if img is None:
            print("[SKILL] 无法读取快照图片，终止。")
            return False

        context = self.ocr.read_screen(img)
        
        ax, ay = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    cur_ax, cur_ay = int(parts[0]), int(parts[1])
                    
                    # 关键补丁：双轴精细屏蔽 (仅遮挡浏览器外框，释放网页边缘内容)
                    if cur_ay < 160 or cur_ax < 20:
                        print(f"[SKILL] 忽略非内容区地标 (Edge Buffer): '{line}' at ({cur_ax}, {cur_ay})")
                        continue
                        
                    ax, ay = cur_ax, cur_ay
                    print(f"[SKILL] 命中【任务核心区】地标文本: '{line}'")
                    break
                except: continue
        
        if ay == -1: 
            if optional:
                print(f"[SKILL] 未找到地标 {keywords}，但由于是可选模式 (Optional)，继续任务。")
                return True
            print(f"[SKILL] 错误: 未能在当前物理快照中找到地标 {keywords}。建议使用 AIM 模式重新校准。")
            return False

        config = self._load_config()
        if not config: return False
        
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        
        # 补丁：只针对真正的任务输入项（如 Inputs/Source/Output）寻找缩略图中心
        # 对于 UI 按钮、标签页、标题、弹窗关闭等，必须直接点在文字中心，绝不偏移！
        task_keywords = ["inputs", "input", "source", "output"]
        use_thumbnail = any(k.lower() in task_keywords for k in keywords)
        
        # 强制排除项：如果命中这些词，绝不使用缩略图模式
        force_direct = ["multimango", "omni", "continue", "取消", "outlier"]
        if any(k.lower() in force_direct for k in keywords):
            use_thumbnail = False
        
        tx, ty = -1, -1
        if use_thumbnail:
            tx_rel, ty_rel = self._find_thumbnail_center(ax, ay, img)
            if tx_rel and ty_rel:
                tx, ty = base_x + tx_rel, base_y + ty_rel
                print(f"[SKILL] 视觉中心定位成功 (缩略图模式): ({tx}, {ty})")
        
        if tx == -1:
            # 对于 UI 按钮和标签页，直接点击文字中心，不加额外偏移
            if any(k.lower() in ["取消", "multimango", "outlier", "omni", "continue"] for k in keywords):
                tx, ty = base_x + ax, base_y + ay
                print(f"[SKILL] UI 精准原位点击: ({tx}, {ty})")
            elif offset_y != 140:
                # 如果用户显式传入了偏移量（包括 0），则严格以此为准
                tx, ty = base_x + ax, base_y + ay + offset_y
                print(f"[SKILL] 遵循显式偏移量点击: ({tx}, {ty}) [Offset: {offset_y}]")
            else:
                # 默认落入针对评分页中文字段落的 4K 适配方案 (原始 140 偏移)
                tx, ty = base_x + ax + 30, base_y + ay + 140
                print(f"[SKILL] 内容文字对位点击 (默认重度偏移模式): ({tx}, {ty})")

        # 全链路高度加固：物理焦点锁定 + 毫秒级原生点击
        import win32gui
        import win32api
        import win32con
        
        # 1. 强制激活并置顶
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except: pass

        # 2. 物理原语级点击 (三连点确保激活)
        print(f"[SKILL] 执行最终物理级点击: ({tx}, {ty})")
        for i in range(2):
            win32api.SetCursorPos((int(tx), int(ty)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)

        time.sleep(1.0) 
        return True

    def action_click_smart(self, keywords=None, rel_x=0, rel_y=0, offset_y=0, optional=False, landmark_image=None, layout_size=None):
        """
        全场景鲁棒点击技能 (V26.1: 集成颜色空间结构对位)
        算法优先级：0. 结构锚点(V26.1) -> 1. 视觉锚点(图标) -> 2. 语义地标(文字) -> 3. 物理对位
        """
        print(f"[SKILL] 智能对位点击 | Keywords: {keywords} | Image: {landmark_image} | Size: {layout_size}")
        
        # 0. V26.1: 尝试结构对位 (基于 V26 变色龙算法)
        if layout_size:
            from src.utils.layout_parser import LayoutParser
            view_path = self.action_screenshot("structural_reanchor")
            img = cv2.imread(view_path)
            if img is not None:
                # 在记录的相对位置执行颜色探测 (假设窗口缩放一致)
                # 我们寻找点击中心 (rel_x, rel_y) 周围的颜色块
                target_block = LayoutParser.detect_color_block(img, rel_x, rel_y)
                if target_block:
                    tbx, tby, tbw, tbh = target_block["rect"]
                    # 如果识别到的块大小与录制时相近 (误差 15%)，认为对位成功
                    if abs(tbw - layout_size[0]) < tbw*0.15 and abs(tbh - layout_size[1]) < tbh*0.15:
                        rect_data = self.wm.get_window_rect()
                        base_x = rect_data["left"] if rect_data else 0
                        base_y = rect_data["top"] if rect_data else 0
                        
                        # 点击目标块的中心
                        tx = base_x + tbx + tbw/2
                        ty = base_y + tby + tbh/2 + offset_y
                        
                        print(f"[SKILL] V26.1 变色龙结构对位成功! -> 点击: ({tx}, {ty})")
                        import win32api, win32con
                        win32api.SetCursorPos((int(tx), int(ty)))
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        time.sleep(0.05)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        return True
        
        # 0. 尝试视觉锚点定位 (V19: Icon Template Match)
        if landmark_image:
            anchor_path = os.path.join(self.records_dir, landmark_image)
            if os.path.exists(anchor_path):
                anchor_img = cv2.imread(anchor_path)
                view_path = self.action_screenshot("landmark_search")
                screen_img = cv2.imread(view_path)
                
                if anchor_img is not None and screen_img is not None:
                    # 使用 OpenCv 进行模板匹配
                    res = cv2.matchTemplate(screen_img, anchor_img, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    if max_val > 0.8:
                        # 匹配成功，计算全局坐标 (图标中心为 30,30 因为锚点是 60x60)
                        rect_data = self.wm.get_window_rect()
                        base_x = rect_data["left"] if rect_data else 0
                        base_y = rect_data["top"] if rect_data else 0
                        
                        tx = base_x + max_loc[0] + 30
                        ty = base_y + max_loc[1] + 30
                        
                        print(f"[SKILL] 视觉锚点(图标)匹配成功! Score: {max_val:.2f} -> 点击: ({tx}, {ty})")
                        import win32api, win32con
                        win32api.SetCursorPos((int(tx), int(ty)))
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        time.sleep(0.05)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        return True

        # 1. 尝试语义定位 (OCR)
        if keywords:
            view_path = self.action_screenshot("smart_search")
            img = cv2.imread(view_path)
            if img is not None:
                context = self.ocr.read_screen(img)
                best_ax, best_ay = -1, -1
                min_dist = 9999
                for line in context.split('\n'):
                    if any(k.lower() in line.lower() for k in keywords):
                        try:
                            parts = line.split("坐标: (")[1].split(")")[0].split(",")
                            ax, ay = int(parts[0]), int(parts[1])
                            # 计算与预期录制位置的相对距离
                            dist = ((ax - rel_x)**2 + (ay - rel_y)**2)**0.5
                            if dist < min_dist:
                                min_dist = dist
                                best_ax, best_ay = ax, ay
                        except: continue
                
                # 如果偏差在 120 像素内，认为语义目标正确
                if best_ay != -1 and min_dist < 120:
                    rect_data = self.wm.get_window_rect()
                    base_x = rect_data["left"] if rect_data else 0
                    base_y = rect_data["top"] if rect_data else 0
                    tx, ty = base_x + best_ax, base_y + best_ay + offset_y
                    
                    print(f"[SKILL] 语义地标(文字)对位成功! 偏差 {min_dist:.1f}px -> 点击: ({tx}, {ty})")
                    import win32api, win32con
                    win32api.SetCursorPos((int(tx), int(ty)))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    return True

        # 2. 兜底方案：物理相对坐标
        rect_data = self.wm.get_window_rect()
        if rect_data:
            tx = rect_data["left"] + rel_x
            ty = rect_data["top"] + rel_y + offset_y
            print(f"[SKILL] 兜底模式 -> DWM 物理点击: ({tx}, {ty})")
            import win32api, win32con
            win32api.SetCursorPos((int(tx), int(ty)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return True
            
        return False

    def action_click_landmark_v2(self, keywords=["Inputs", "Earnings"], search_depth=400, optional=False):
        """原子积木 V2：语义级视觉吸附探测 (实验性方案)"""
        print(f"[SKILL-V2] 启动语义视觉搜索，目标锚点: {keywords}")
        
        import win32gui, win32api, win32con
        import numpy as np

        # 1. 强力对焦锁定
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except: pass

        # 2. 状态快照
        view_path = self.action_screenshot("semantic_search")
        img = cv2.imread(view_path)
        if img is None: return False
        
        # 3. OCR 锚点定位
        context = self.ocr.read_screen(img)
        ax, ay = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    cur_ax, cur_ay = int(parts[0]), int(parts[1])
                    if cur_ay < 160 or cur_ax < 20: continue # 沿用防误触禁区
                    ax, ay = cur_ax, cur_ay
                    print(f"[SKILL-V2] 物理锚点锁定: '{line}' at ({ax}, {ay})")
                    break
                except: continue
        
        if ay == -1:
            if optional: return True
            print(f"[SKILL-V2] 锚点未见，搜索失败。")
            return False

        # 4. 语义视觉探测 (OpenCV 魔法时间)
        h, w, _ = img.shape
        # 定义搜索扇区: 文字正下方 400px，左右各扩散 200px
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
            # 过滤逻辑：符合图标/卡片大小，且不能太扁或太细
            if 1000 < area < 40000 and 0.4 < (w_c/h_c) < 2.5:
                # 计算与锚点文字底边缘的距离（越近越好）
                dist = y_c 
                candidates.append({
                    'center': (x_c + w_c//2, y_c + h_c//2),
                    'dist': dist,
                    'rect': (x_c, y_c, w_c, h_c)
                })
                cv2.rectangle(debug_img, (x_c, y_c), (x_c+w_c, y_c+h_c), (255, 0, 0), 2)

        final_tx, final_ty = -1, -1
        if candidates:
            # 排序寻找最符合“紧邻文字下方”特征的那个块
            candidates.sort(key=lambda x: x['dist'])
            best = candidates[0]
            final_tx, final_ty = roi_x1 + best['center'][0], roi_y1 + best['center'][1]
            # 视觉反馈回填
            cv2.drawMarker(debug_img, best['center'], (0, 255, 0), cv2.MARKER_CROSS, 30, 3)
            print(f"[SKILL-V2] 语义特征吸附成功: ({final_tx}, {final_ty})")
        
        # 保存诊断图
        debug_path = os.path.join(r"D:\Dev\autoplay\records", "semantic_debug.jpg")
        cv2.imwrite(debug_path, debug_img)
        
        if final_tx == -1:
            print("[SKILL-V2] 未能识别到显著特征块，降级使用物理偏移。")
            final_tx, final_ty = ax + 30, ay + 140 # 降级回版本 1
        
        # 5. 执行物理原语点击
        config = self._load_config()
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        real_tx, real_ty = base_x + final_tx, base_y + final_ty
        
        for i in range(2):
            win32api.SetCursorPos((int(real_tx), int(real_ty)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)
            
        print(f"[SKILL-V2] 执行完成。")
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
                print(f"[SKILL] 探测到潜在缩略图区域: {rw}x{rh}")
                return rx + max(ax-100, 0) + rw // 2, ry + ay + rh // 2
        return None, None

    def action_wait_visual(self, threshold=5.0, timeout=12):
        """原子积木：视觉变化等待 (已增敏)"""
        config = self._load_config()
        if not config: return False
        raw = config["dock_rect"]
        monitor = {"left": raw["x"], "top": raw["y"], "width": raw["width"], "height": raw["height"]}
        
        print(f"[SKILL] 正在监测画面变化 (阈值: {threshold}%, 超时: {timeout}s)...")
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
                    print(f"[SKILL] 检测到画面变化完成! ({change_val:.2f}%)")
                    return True
                time.sleep(0.5)
        print("[SKILL] 画面监测超时，未发现预期变化。")
        return False

    def action_press_keys(self, keys=["down"], interval=0.5):
        """原子积木：按键序列注入 (由 Agent 处理随机间隔)"""
        print(f"[SKILL] 注入按键: {keys}, 预设间隔: {interval}")
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
        原子积木：深度巡航控制 (物理内核硬化版)
        """
        import win32gui, win32api, win32con
        print(f"\n[SKILL] 正在执行 Win32 暴力巡航: {landmark_keywords}")

        # --- Step 1: 物理激活与视图自动回正 ---
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except: pass

        # 辅助对位：执行前发送物理 LEFT，确保在 Response A
        # 补丁：连点两次并增加时延，确保 UI 状态机在远程桌面上完成切换
        for _ in range(2):
            win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.2)
        time.sleep(0.8)

        # --- Step 1: 找到地标位置 ---
        view_path = self.action_screenshot("ref_search")
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)

        ax, ay = -1, -1
        # 预加载容错关键词：针对常见的 OCR 误读进行静默增强
        if any(k.lower() in ["response", "response a", "response b"] for k in landmark_keywords):
            landmark_keywords = list(set(landmark_keywords + ["rosponse", "respon", "rospon", "rosponse a", "rosponse b", "rbbponse", "rason", "roso"]))

        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in landmark_keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    cur_ax, cur_ay = int(parts[0]), int(parts[1])
                    
                    # 关键补丁：双轴过滤，防止误触浏览器 UI
                    if cur_ay < 160 or cur_ax < 20: 
                        print(f"[SKILL] 忽略非对焦区地标 (Anti-Interference): '{line}' at ({cur_ax}, {cur_ay})")
                        continue
                        
                    ax, ay = cur_ax, cur_ay
                    print(f"[SKILL] 命中物理巡航锚点: ({ax}, {ay})")
                    break
                except: continue

        if ay == -1:
            print(f"[SKILL] 警告: 未能发现地标 {landmark_keywords}，启用中心点对焦兜底。")
            config = self._load_config()
            ax, ay = config['dock_rect']['width'] // 2, config['dock_rect']['height'] // 2

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # --- 最终物理内核执行序列 ---
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
        print(f"[SKILL] 执行 Win32 物理对焦 ({target_x}, {target_y}) 与缩放 x{actual_scroll}")
        
        for _ in range(3):
            win32api.SetCursorPos((target_x, target_y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)

        for _ in range(abs(actual_scroll)):
            # 根据正负号决定方向 (120 为向上/放大, -120 为向下/缩小)
            direction = 120 if actual_scroll > 0 else -120
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, direction, 0)
            time.sleep(0.05)
        time.sleep(0.6)

        print(f"[SKILL] 执行物理流平移: dx={pan_dx}, dy={pan_dy}")
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
            print("[SKILL] 执行物理双击还原")
            win32api.SetCursorPos((target_x, target_y))
            for _ in range(2):
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.05)

        return True

    def action_zoom(self, amount=5):
        """原子积木：纯粹的物理滚轮缩放 (支持随机)"""
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
            
        print(f"[SKILL] 执行物理缩放: {actual_amount}")
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
        原子积木 - 第 5 步完整链路:
        1. 点击 SOURCE 左侧缩略图
        2. 按下向下方向键触发导航
        3. 等待右侧 Response A 大图出现
        4. 点击该大图
        5. 滚轮 Zoom In
        6. 按住左键绕圆圈 PAN
        7. 双击还原
        """
        import pydirectinput
        import win32api, win32con, math

        print(f"\n[SKILL] 执行 Source->Down->ResponseA->Zoom->Circle->Reset")

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # Step 1: OCR 找 SOURCE 地标
        view_path = self.action_screenshot("source_nav")
        img = cv2.imread(view_path)
        context = self.ocr.read_screen(img)
        src_x, src_y = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in source_keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    src_x, src_y = int(parts[0]), int(parts[1])
                    break
                except: continue

        if src_y == -1:
            print("[SKILL] 未找到 SOURCE，终止。")
            return False

        # 点击 SOURCE 下方小图标
        self.agent.click_at(base_x + src_x, base_y + src_y + 80)
        time.sleep(0.5)

        # Step 2: 按下方向键
        pydirectinput.keyDown('down'); time.sleep(0.15); pydirectinput.keyUp('down')
        time.sleep(1.0)

        # Step 3: 等待 Response A 出现 (已增敏)
        self.action_wait_visual(threshold=5.0, timeout=8)

        # Step 4: 重新截图找 Response A 大图
        img2 = cv2.imread(self.action_screenshot("response_a"))
        context2 = self.ocr.read_screen(img2)
        resp_x, resp_y = -1, -1
        for line in context2.split('\n'):
            if any(k.lower() in line.lower() for k in response_keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    resp_x, resp_y = int(parts[0]), int(parts[1])
                    break
                except: continue

        if resp_y == -1:
            print("[SKILL] 未找到 Response A，终止。")
            return False

        # Response A 文字右侧大图（+偏移）
        img_x = base_x + resp_x + 150
        img_y = base_y + resp_y + 60
        self.agent.click_at(img_x, img_y)
        time.sleep(0.4)

        # Step 5: 滚轮 Zoom In
        pydirectinput.moveTo(img_x, img_y)
        for _ in range(scroll_amount):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
            time.sleep(0.15)
        time.sleep(0.5)

        # Step 6: 圆圈 PAN
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

        # Step 7: 双击还原
        pydirectinput.doubleClick(img_x, img_y)
        time.sleep(0.3)
        print("[SKILL] Source->Navigate->Zoom->Circle->Reset 完成。")
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
        原子积木 - 第 6 步完整链路（反向大圆圈版）:
        1. 点击 OUTPUT 下方左侧小图标
        2. 按下向右方向键
        3. 等待 Response B 出现
        4. 点击 Response B 大图
        5. Zoom In 大幅放大
        6. Zoom Out 缩回
        7. Zoom In 微调放大
        8. 反方向大圆圈 PAN（逆时针）
        9. 双击还原
        """
        import pydirectinput
        import win32api, win32con, math

        print(f"\n[SKILL] 执行 Output->Right->ResponseB->ZoomInOut->ReversePAN->Reset")

        config = self._load_config()
        if not config: return False
        base_x = config['dock_rect']['x']
        base_y = config['dock_rect']['y']

        # Step 1: OCR 找 OUTPUT 地标
        img = cv2.imread(self.action_screenshot("output_nav"))
        context = self.ocr.read_screen(img)
        out_x, out_y = -1, -1
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in output_keywords):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    out_x, out_y = int(parts[0]), int(parts[1])
                    print(f"[DEBUG] 找到 OUTPUT 文字坐标: ({out_x}, {out_y})")
                    break
                except: continue

        if out_y == -1:
            print("[SKILL] 未找到 OUTPUT，终止。")
            return False

        # 计算图标物理坐标：通常图标在文字下方，左侧图标稍微偏左
        target_icon_x = base_x + out_x - 40 
        target_icon_y = base_y + out_y + 90
        
        # --- 增强视觉表现：先移动到位置 ---
        print(f"[SKILL] 正在移动到 OUTPUT 图标: ({target_icon_x}, {target_icon_y})")
        pydirectinput.moveTo(target_icon_x, target_icon_y, duration=0.5) 
        time.sleep(0.3)
        
        # 激活窗口确保按键有效
        self.agent.activate_window(self.agent.profile_name) 
        
        # 确切点击
        self.agent.click_at(target_icon_x, target_icon_y)
        time.sleep(0.5)

        # Step 2: 按右方向键
        print("[SKILL] 发送 RIGHT 方向键控制...")
        pydirectinput.press('right')
        
        # --- Step 3: 极致鲁棒等待 Response B (模糊匹配 + 按键重试) ---
        print("[SKILL] 正在等待右侧 Response B 加载...")
        wait_start = time.time()
        resp_x, resp_y = -1, -1
        has_retried_key = False
        
        while time.time() - wait_start < 15: # 延长到15秒
            view_path = self.action_screenshot("polling_resp_b")
            img2 = cv2.imread(view_path)
            context2 = self.ocr.read_screen(img2)
            
            for line in context2.split('\n'):
                l_line = line.lower()
                # 模糊匹配：只要有 response 且在右半区 (base_x+300以右)
                if "response" in l_line and "response a" not in l_line:
                    try:
                        parts = line.split("坐标: (")[1].split(")")[0].split(",")
                        cur_x, cur_y = int(parts[0]), int(parts[1])
                        
                        # 位置校验：Response B 必在右侧
                        if cur_x > 350: 
                            resp_x, resp_y = cur_x, cur_y
                            print(f"[SKILL] 模糊匹配锁定右侧目标: {line}")
                            break
                    except: continue
            
            if resp_x != -1: break
            
            # 补丁：如果等待超过 4 秒还没动静，可能是按键丢了，重按一次
            if (time.time() - wait_start) > 4.0 and not has_retried_key:
                print("[SKILL] 页面未响应，尝试重按 RIGHT 键...")
                pydirectinput.press('right')
                has_retried_key = True

            print(f"[SKILL] 搜索中... (已等 {int(time.time()-wait_start)}s)")
            time.sleep(1.2)

        if resp_x == -1:
            print("[SKILL] 严重警告: 15秒内未能在右侧锁定目标。")
            return False

        # --- Step 4: 渲染缓冲 (给大图片 2.0 秒加载时间) ---
        print("[SKILL] 目标已锁定，正在等待高清大图稳定渲染...")
        time.sleep(2.0)

        # 最终确定大图中心坐标 (Response B 文字右侧)
        img_x = base_x + resp_x + 150
        img_y = base_y + resp_y + 60
        
        print(f"[SKILL] 渲染就绪，准备开始变速缩放交互...")
        self.agent.click_at(img_x, img_y)
        time.sleep(0.4)
        pydirectinput.moveTo(img_x, img_y)

        def scroll(amount, direction=1):
            for _ in range(abs(amount)):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120 * direction, 0)
                time.sleep(0.15)

        # Step 5: 大幅 Zoom In
        print(f"[SKILL] Zoom In 大 x{zoom_in_big}")
        scroll(zoom_in_big, 1)
        time.sleep(0.4)

        # Step 6: Zoom Out
        print(f"[SKILL] Zoom Out x{zoom_out}")
        scroll(zoom_out, -1)
        time.sleep(0.4)

        # Step 7: 微幅 Zoom In
        print(f"[SKILL] Zoom In 小 x{zoom_in_small}")
        scroll(zoom_in_small, 1)
        time.sleep(0.5)

        # Step 8: 反方向大圆圈 PAN（逆时针，angle 递减）
        print(f"[SKILL] 逆时针大圆圈 PAN (R={circle_radius})")
        pydirectinput.moveTo(img_x + circle_radius, img_y)
        pydirectinput.mouseDown(button='left')
        time.sleep(0.1)
        for step in range(circle_steps + 1):
            angle = -2 * math.pi * step / circle_steps  # 负号 = 逆时针
            pydirectinput.moveTo(
                img_x + int(circle_radius * math.cos(angle)),
                img_y + int(circle_radius * math.sin(angle))
            )
            time.sleep(0.04)
        pydirectinput.mouseUp(button='left')
        time.sleep(0.5)

        # Step 9: 双击还原
        pydirectinput.doubleClick(img_x, img_y)
        time.sleep(0.3)
        print("[SKILL] Output->Right->ResponseB->Zoom->ReversePAN->Reset 完成。")
        return True

    def action_scroll_home_end(self, direction="end"):
        """原子积木：最高等级物理滚动 (内容区对焦版)"""
        import pydirectinput
        print(f"[SKILL] 正在启动内容区强力滚动: {direction}")
        
        self.agent.activate_window(self.agent.profile_name)
        time.sleep(0.3)
        
        config = self._load_config()
        if not config: return False
        
        # 核心改进：寻找内容区的标志性地标文字进行对焦点击，确保滚动针对内容窗格
        # 针对 4K 竖屏扩充关键词雷达: 加入 Elo, Guidelines, Mango 等
        view_path = self.action_screenshot("scroll_focus")
        img = cv2.imread(view_path)
        if img is None: return False
        
        context = self.ocr.read_screen(img)
        
        focus_x, focus_y = -1, -1
        target_kws = ["inputs", "omni", "source", "response", "tina", "elo", "guidelines", "mango", "multimango"]
        for line in context.split('\n'):
            if any(k.lower() in line.lower() for k in target_kws):
                try:
                    parts = line.split("坐标: (")[1].split(")")[0].split(",")
                    ax, ay = int(parts[0]), int(parts[1])
                    
                    # 关键补丁：双轴坐标过滤 (精修版)
                    # 1. 忽略窗口顶部 160 像素内的地标（仅遮挡标签栏/地址栏/书签栏）
                    # 2. 忽略极窄侧边 20 像素内的地标（基本防误触）
                    if ay < 160 or ax < 20:
                        print(f"[SKILL] 忽略非内容区地标 (System UI Buffer): '{line}' at ({ax}, {ay})")
                        continue
                        
                    focus_x = config['dock_rect']['x'] + ax
                    focus_y = config['dock_rect']['y'] + ay
                    print(f"[SKILL] 命中【任务核心区】地标 '{line}'，执行点击对焦...")
                    break
                except: continue
                
        if focus_x == -1:
            # 降级方案：点击目标窗口左侧 1/4 处，确保避开中间空窗区
            print("[SKILL] 未发现地标文案，启动区域纠偏对焦 (Region-Based)...")
            focus_x = config['dock_rect']['x'] + (config['dock_rect']['width'] // 4)
            focus_y = config['dock_rect']['y'] + (config['dock_rect']['height'] // 3)
            
        # 全链路加固：强制物理焦点锁定
        import win32gui
        import win32api
        import win32con
        
        # 1. 强力激活目标窗口 (Window-Level Focus)
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
        if hwnd:
            print(f"[SKILL] 正在强制置顶目标窗口 [HWND:{hwnd}]...")
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except Exception as e:
                print(f"[SKILL] 窗口置顶提示: {e}")

        # 执行三连击确保激活容器 (改用底层 win32api 绕过 pydirectinput 的远程环境卡顿)
        for i in range(3):
            print(f"[SKILL] 正在执行底层对焦点击 {i+1}/3 (物理坐标: {focus_x}, {focus_y})...")
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
            
        print(f"[SKILL] 激活完成，立即通过 Win32 注入 {main_key_name} x{burst_count} 物理连发...")
        for i in range(burst_count):
            # 模拟按下和抬起 (增加按下时长，确保远程环境捕获)
            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.03) # 增加按住时间 (Hold time)
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            if i % 5 == 0: print(f"[SKILL] 滚动进度: {i}/{burst_count}...")
            time.sleep(0.08) # 增加间隔时间 (Inter-key delay)
            
        # 滚轮长效补丁
        print(f"[SKILL] 正在注入硬件级滚轮补丁...")
        for _ in range(12):
            amount = -1200 if is_end else 1200
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            time.sleep(0.06)
            
        print(f"[SKILL] 内容区全链路暴力滚动已完成")
        time.sleep(0.8) 
        return True

    def action_close_tab(self):
        """原子积木：关闭当前浏览器标签页 (Ctrl+W)"""
        import pydirectinput
        self.agent.activate_window(self.agent.profile_name)
        time.sleep(0.3)
        print("[SKILL] 正在关闭当前标签页 (Ctrl+W)...")
        pydirectinput.keyDown('ctrl')
        pydirectinput.press('w')
        pydirectinput.keyUp('ctrl')
        time.sleep(0.5)
        return True

    def action_click_raw(self, rel_x, rel_y):
        """
        原子积木：相对物理点击 (录制器回退方案)
        基于对位基准的偏移点击，确保窗口移动后依然有效。
        """
        import win32api, win32con, win32gui
        config = self._load_config()
        if not config: return False
        
        base_x, base_y = config['dock_rect']['x'], config['dock_rect']['y']
        abs_x, abs_y = base_x + rel_x, base_y + rel_y
        
        print(f"[SKILL] 执行物理点击: ({abs_x}, {abs_y}) [Rel: {rel_x}, {rel_y}]")
        
        # 强制激活窗口确保点击有效
        hwnd = win32gui.FindWindow(None, self.agent.profile_name)
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
        """原子积木：支持固定或随机延时等待 (V27.5)"""
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
            
        print(f"[SKILL] 延时等待 {final_seconds:.2f} 秒...")
        time.sleep(final_seconds)
        return True
