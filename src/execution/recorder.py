import time
import threading
import win32api
import win32con
import win32gui
import os
import cv2
import numpy as np
from typing import Callable, Optional
import mss
from src.utils.vision import VisionCapture
from src.utils.layout_parser import LayoutParser

class MissionRecorder:
    """
    智能录制机：监听用户物理操作并将其转化为原子积木流。
    支持语义级对位（OCR 自动识别）与时间间隙自动补全。
    """
    def __init__(self, bridge, hardware_manager, skills):
        self.bridge = bridge
        self.hw = hardware_manager
        self.skills = skills # 用于截图和 OCR
        self.is_recording = False
        self.last_action_time = 0
        self.thread = None
        
    def start(self):
        self.is_recording = True
        self.last_action_time = time.time()
        self.thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.thread.start()
        print("[RECORDER] 录制引擎启动，正在侦听物理输入...")

    def stop(self):
        self.is_recording = False
        print("[RECORDER] 录制引擎已安全停止。")

    def _get_dock_rect(self):
        config = self.hw.get_active_calibration()
        if config:
            return config.get("dock_rect")
        return None

    def _recording_loop(self):
        # 记录按键状态以检测“按下”瞬间
        last_lbutton_state = False
        last_keys_state = {} 
        
        while self.is_recording:
            # 1. 鼠标左键检测 (VK_LBUTTON = 0x01)
            # 使用 GetAsyncKeyState 检测物理按键状态
            lbutton_state = win32api.GetAsyncKeyState(0x01) & 0x8000
            if lbutton_state and not last_lbutton_state:
                # 瞬间按下
                self._handle_click_event()
            last_lbutton_state = lbutton_state
            
            # 2. 键盘关键按键检测 (方向键、回车)
            vks = [win32con.VK_LEFT, win32con.VK_RIGHT, win32con.VK_UP, win32con.VK_DOWN, win32con.VK_RETURN]
            for vk in vks:
                state = win32api.GetAsyncKeyState(vk) & 0x8000
                if state and not last_keys_state.get(vk, False):
                    self._handle_key_event(vk)
                last_keys_state[vk] = state
                
            time.sleep(0.04) # 25Hz 轮询，平衡灵敏度与性能

    def _handle_click_event(self):
        # --- V16 暴力日志：确认后台线程是否唤醒 ---
        self.bridge._log(">>> 捕捉到物理鼠标点击事件 (CLICK DETECTED)")
        
        # 获取物理坐标 (含 DPI 缩放下的真实物理坐标)
        x, y = win32api.GetCursorPos()
        self.bridge._log(f"[RECORDER] 点击位置: physical_x={x}, physical_y={y}")
        
        # --- V14 关键优化：实时获取 DWM 物理边界，不再依赖静态配置 ---
        # 我们使用 skills.wm 来实时获取当前窗口的 DWM 物理像素矩形
        rect_data = self.skills.wm.get_window_rect()
        if not rect_data: 
            self.bridge._log("[RECORDER] 无法探测到合法的目标窗口 (No Window Rect)")
            return
        
        self.bridge._log(f"[RECORDER] 当前目标窗口: '{rect_data['title']}' Rect: {rect_data['left']},{rect_data['top']} @ {rect_data['width']}x{rect_data['height']}")
        
        # 将 "left", "top" 格式转换为 "x", "y" 以匹配内部逻辑
        rect = {
            "x": rect_data["left"],
            "y": rect_data["top"],
            "width": rect_data["width"],
            "height": rect_data["height"]
        }
        
        # 范围校验 (确保只记录目标窗口内的操作)
        if not (rect['x'] <= x <= rect['x'] + rect['width'] and 
                rect['y'] <= y <= rect['y'] + rect['height']):
            self.bridge._log(f"[RECORDER] 点击发生在窗口外，跳过记录。")
            return

        # 转换为相对坐标 (对位基准)
        rel_x = x - rect['x']
        rel_y = y - rect['y']
        
        self.bridge._log(f"[RECORDER] 转换相对物理坐标成功: rel_x={rel_x}, rel_y={rel_y}")
        
        # 录制等待步
        self._record_wait_step()
        
        # 智能语义转换：尝试识别 landmark
        step = self._generate_smart_click(rel_x, rel_y)
        self.bridge.add_recorded_step(step)
        
        self.last_action_time = time.time()

    def _handle_key_event(self, vk):
        self._record_wait_step()
        
        key_map = {
            win32con.VK_LEFT: "left",
            win32con.VK_RIGHT: "right",
            win32con.VK_UP: "up",
            win32con.VK_DOWN: "down",
            win32con.VK_RETURN: "enter"
        }
        key_name = key_map.get(vk, "unknown")
        
        step = {
            "name": f"按键操作: {key_name.upper()}",
            "action": "action_press_keys",
            "params": {"keys": [key_name]},
            "description": f"手动录制的键盘操作: {key_name}"
        }
        self.bridge.add_recorded_step(step)
        self.last_action_time = time.time()

    def _record_wait_step(self):
        now = time.time()
        duration = now - self.last_action_time
        # 只有在间隔显著时（>0.7s）才创建等待步
        if duration > 0.7:
            wait_step = {
                "name": f"等待 {duration:.1f}s",
                "action": "action_sleep",
                "params": {"seconds": round(duration, 1)},
                "description": "录制产生的自动延时"
            }
            self.bridge.add_recorded_step(wait_step)

    def _generate_smart_click(self, rx, ry):
        """
        语义级识别核心：
        利用截图 + EasyOCR 实时探测鼠标点击位置是否有文字。
        如果有，优先生成 Landmark 积木，极大增强脚本鲁棒性。
        """
        print(f"[RECORDER] 语义分析中 -> Rel: ({rx}, {ry})")
        
        with mss.mss() as sct:
            rect = self._get_dock_rect()
            # V23: 广角模式 (Panorama Rule) - 极大视野以确保大方块闭合
            monitor = {
                "left": int(rect['x'] + rx - 300), 
                "top": int(rect['y'] + ry - 200), 
                "width": 600, 
                "height": 400
            }
            
            try:
                # V13 瞬时红准星反馈
                if self.bridge.on_visual_feedback_cb:
                    self.bridge._log(f"[RECORDER] 发送【瞬时准星】信号: rx={rx}, ry={ry}")
                    self.bridge.on_visual_feedback_cb(rx - 10, ry - 10, 20, 20, 0)

                # 1. 广角捕获 (用于结构分析)
                screenshot = np.array(sct.grab(monitor))
                rgb_img = cv2.cvtColor(screenshot, cv2.COLOR_RGBA2RGB)
                
                # --- V26: 变色龙颜色追踪 (Color-Snap) ---
                # 针对无边框设计，通过点击点的颜色倾向反向寻找组件闭合区域
                target_block = LayoutParser.detect_color_block(rgb_img, 300, 200)
                
                if not target_block:
                    # 如果颜色追踪失败，退回到传统的形态学结构检测
                    blocks = LayoutParser.detect_blocks(rgb_img)
                    target_block = LayoutParser.find_containing_block(blocks, 300, 200) 
                
                # --- V24+: 视觉镜像调试 (Vision Mirror) ---
                try:
                    debug_map = rgb_img.copy()
                    if target_block:
                        tbx, tby, tbw, tbh = target_block["rect"]
                        # 选中的块画红线
                        cv2.rectangle(debug_map, (tbx, tby), (tbx+tbw, tby+tbh), (0, 0, 255), 2)
                    
                    vision_map_path = r"D:\Dev\autoplay\records\last_vision_map.png"
                    cv2.imwrite(vision_map_path, cv2.cvtColor(debug_map, cv2.COLOR_RGB2BGR))
                except Exception as de:
                    self.bridge._log(f"[RECORDER] 视觉镜像生成失败: {de}")

                if target_block:
                    bx, by, bw, bh = target_block["rect"]
                    self.bridge._log(f"[RECORDER] V26 捕获槽位: {bw}x{bh} at ({bx},{by})")
                    # 发送黄色结构反馈 (v_type=3)
                    if self.bridge.on_visual_feedback_cb:
                        rel_bx = rx - 300 + bx
                        rel_by = ry - 200 + by
                        self.bridge.on_visual_feedback_cb(int(rel_bx), int(rel_by), int(bw), int(bh), 3)

                # 2. 局部高精 OCR (保持 2x 采样，仅取中心 ROI 区域)
                # 在 600x400 中，中心 240x80 区域对应 [160:240, 180:420]
                ocr_roi = rgb_img[160:240, 180:420]
                upscaled = cv2.resize(ocr_roi, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
                
                # --- V12 照妖镜逻辑：保存画面 ---
                try:
                    eye_path = r"D:\Dev\autoplay\records\recorder_eye.png"
                    cv2.imwrite(eye_path, cv2.cvtColor(upscaled, cv2.COLOR_RGB2BGR))
                    # 同时保存广角视口诊断
                    debug_path = r"D:\Dev\autoplay\records\wide_eye.png"
                    cv2.imwrite(debug_path, cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR))
                except: pass
                
                # 调用 OCR 识别
                results = self.skills.ocr.reader.readtext(upscaled)
                
                if results:
                    # V18: 狙击模式 (针对 OCR_ROI 的映射中心点是 240, 80)
                    def get_dist(item):
                        box = item[0]
                        cx = sum(p[0] for p in box) / 4
                        cy = sum(p[1] for p in box) / 4
                        return (cx - 240)**2 + (cy - 80)**2
                    
                    results.sort(key=get_dist)
                    bbox, text, prob = results[0]
                    text = text.strip()
                    
                    if 2 <= len(text) <= 15:
                        self.bridge._log(f"[RECORDER] 高精语义捕捉成功: '{text}' (Confidence: {prob:.2f})")
                        
                        try:
                            if self.bridge.on_visual_feedback_cb:
                                # 相对 ROI 起点的偏移 rx-120, ry-40
                                rel_x_start = rx - 120
                                rel_y_start = ry - 40
                                x_coords = [p[0] for p in bbox]
                                y_coords = [p[1] for p in bbox]
                                bx_v = int(min(x_coords) / 2 + rel_x_start)
                                by_v = int(min(y_coords) / 2 + rel_y_start)
                                bw_v = int((max(x_coords) - min(x_coords)) / 2)
                                bh_v = int((max(y_coords) - min(y_coords)) / 2)
                                self.bridge.on_visual_feedback_cb(bx_v, by_v, bw_v, bh_v, 0)
                        except Exception as ve:
                            self.bridge._log(f"[RECORDER] 视觉反馈计算失败: {ve}")

                        layout_info = (target_block["rect"][2], target_block["rect"][3]) if target_block else None
                        return {
                            "name": f"点击文字 '{text}'",
                            "action": "action_click_smart",
                            "params": {
                                "keywords": [text], 
                                "rel_x": rx, 
                                "rel_y": ry, 
                                "offset_y": 0, 
                                "optional": True,
                                "layout_size": layout_info
                            },
                            "description": f"录制器产生的混合对位积木 (Text: {text})"
                        }
                # --- V19: 如果没有文字结果，尝试捕捉图标锚点 ---
                self.bridge._log(f"[RECORDER] 未发现清晰文字，切换至【视觉锚点】模式")
                icon_img = rgb_img[10:70, 90:150]
                icon_filename = f"anchor_{int(time.time())}.png"
                icon_path = os.path.join(self.records_dir, icon_filename)
                cv2.imwrite(icon_path, cv2.cvtColor(icon_img, cv2.COLOR_RGB2BGR))
                
                # 发送绿色准星反馈 (v_type=1)
                if self.bridge.on_visual_feedback_cb:
                    self.bridge.on_visual_feedback_cb(rx - 15, ry - 15, 30, 30, 1)

                layout_info = (target_block["rect"][2], target_block["rect"][3]) if target_block else None
                return {
                    "name": f"点击图标 @({rx}, {ry})",
                    "action": "action_click_smart",
                    "params": {
                        "rel_x": rx, 
                        "rel_y": ry, 
                        "landmark_image": icon_filename,
                        "layout_size": layout_info
                    },
                    "description": "视觉锚点对位点击"
                }
            except Exception as e:
                self.bridge._log(f"[RECORDER] 语义分析失败: {e}")

        # 降级方案：使用相对物理坐标
        layout_info = (target_block["rect"][2], target_block["rect"][3]) if 'target_block' in locals() and target_block else None
        return {
            "name": f"相对点击 ({rx}, {ry})",
            "action": "action_click_smart",
            "params": {
                "rel_x": rx, 
                "rel_y": ry,
                "layout_size": layout_info
            },
            "description": "未检测到语义地标，回退至物理坐标"
        }
