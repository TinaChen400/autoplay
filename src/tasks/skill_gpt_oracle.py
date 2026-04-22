import os
import time
import io
import win32gui
import win32con
import win32api
import win32clipboard
import win32com.client
import pyautogui
import mss
import numpy as np
import cv2
import pythoncom
from PIL import Image

class GPTOracle:
    """
    V27 GPT 跨维度决策引擎 (LLM Decision Engine)
    负责本机 Chrome/GPT 的自动化编排与决策解析。
    """
    def __init__(self, bridge=None):
        self.bridge = bridge
        self.records_dir = r"D:\Dev\autoplay\records"
        # 默认提示词
        self.system_prompt = "这是Tina控制对象的实时截图。请根据任务要求分析并给出决策。只需返回答案本身（如 'A' 或 'B'）。"
        
        # V28 新增属性
        self.image_queue = [] # 图片队列，存储 PIL 对象
        self.cached_hwnd = None # 浏览器窗口句柄缓存
        self.last_extraction_success = False

    def _log(self, msg):
        if self.bridge:
            self.bridge._log(f"[ORACLE] {msg}")
        else:
            print(f"[ORACLE] {msg}")

    def action_clear_queue(self):
        """清空图片队列"""
        self.image_queue = []
        self._log("图片队列已清空")

    def action_add_to_queue(self, dock_rect):
        """捕获当前 Dock 画面并存入内存队列"""
        try:
            with mss.mss() as sct:
                # 兼容性处理：支持 top/left 和 y/x 两种 key
                top = int(dock_rect.get("top", dock_rect.get("y", 0)))
                left = int(dock_rect.get("left", dock_rect.get("x", 0)))
                monitor = {
                    "top": top, 
                    "left": left,
                    "width": int(dock_rect["width"]),
                    "height": int(dock_rect["height"])
                }
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                self.image_queue.append(img)
                self._log(f"画面已加入队列 (当前长度: {len(self.image_queue)})")
                return True
        except Exception as e:
            self._log(f"加入队列失败: {e}")
            return False

    def action_capture_to_clipboard(self, dock_rect):
        """兼容旧版：清空队列并加入单张图"""
        self.action_clear_queue()
        return self.action_add_to_queue(dock_rect)

    def action_add_file_to_queue(self, file_path):
        """将磁盘上的文件（如叠合图）加入投喂队列"""
        try:
            if os.path.exists(file_path):
                img = Image.open(file_path)
                self.image_queue.append(img)
                self._log(f"外部文件已加入队列: {os.path.basename(file_path)}")
                return True
        except Exception as e:
            self._log(f"加入外部文件失败: {e}")
            return False

    def action_focus_gpt_window(self):
        """寻找并激活浏览器窗口 (V28 缓存加速版)"""
        pythoncom.CoInitialize()
        try:
            # 1. 优先尝试缓存的句柄
            if self.cached_hwnd and win32gui.IsWindow(self.cached_hwnd) and win32gui.IsWindowVisible(self.cached_hwnd):
                title = win32gui.GetWindowText(self.cached_hwnd).lower()
                if any(k in title for k in ["chatgpt", "doubao", "chrome", "edge"]):
                    self._activate_hwnd(self.cached_hwnd)
                    return True

            # 2. 缓存失效，重新全域搜索
            candidates = []
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    if any(k in title for k in ["chatgpt", "doubao", "豆包", "google chrome", "microsoft edge"]):
                        candidates.append(hwnd)
                return True
            win32gui.EnumWindows(callback, None)

            if not candidates:
                self._log("未找到任何浏览器窗口，请确保已打开豆包/ChatGPT")
                return False

            # 优先逻辑：找到包含豆包或 chatgpt 的
            target = candidates[0]
            for hwnd in candidates:
                t = win32gui.GetWindowText(hwnd).lower()
                if any(k in t for k in ["chatgpt", "doubao", "豆包"]):
                    target = hwnd
                    break
            
            self.cached_hwnd = target
            self._activate_hwnd(target)
            return True
        finally:
            pythoncom.CoUninitialize()

    def _activate_hwnd(self, hwnd):
        """物理激活窗口内核"""
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys('%') # 破解 Win10 焦点限制
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
        except: pass

    def action_send_queue_to_gpt(self, custom_prompt=None):
        """将队列中的所有图片连选粘贴并发送指令 (V28 爆发式投喂)"""
        if not self.image_queue:
            self._log("错误: 队列为空，无可投喂内容")
            return False

        try:
            # 1. 批量粘贴图片
            for i, img in enumerate(self.image_queue):
                self._put_img_to_clipboard(img)
                pyautogui.hotkey('ctrl', 'v')
                self._log(f"已粘贴第 {i+1}/{len(self.image_queue)} 张图片")
                time.sleep(1.2) # 留出上传缓冲

            # 2. 注入提示词
            prompt = custom_prompt if custom_prompt else self.system_prompt
            self._copy_text_to_clipboard(prompt)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            
            # 3. 发送
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'enter') # 双重保险
            
            self._log("全量图片与指令已投喂")
            return True
        except Exception as e:
            self._log(f"投喂失败: {e}")
            return False

    def action_send_to_gpt(self, custom_prompt=None):
        """兼容旧版：发送队列内容"""
        return self.action_send_queue_to_gpt(custom_prompt)

    def _put_img_to_clipboard(self, img):
        """将 PIL Image 转换为 DIB 并存入剪贴板"""
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        finally:
            win32clipboard.CloseClipboard()

    def _copy_text_to_clipboard(self, text):
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    def action_wait_for_gpt_complete(self, timeout=30):
        """
        [V28 新增] 监听豆包“发送”按钮的状态
        判断 AI 是否已经回答完毕（按钮从‘停止’变回‘发送’）
        """
        self._log("正在监听 AI 响应状态...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 这里可以通过 OCR 寻找页面右下角的图标特征，或者简单的固定等待
            # 为了稳定性，我们先结合“文字特征”探测
            time.sleep(2)
            # 模拟：通过简单的时间和状态判断，后期可升级为视觉探测
            if time.time() - start_time > 10: # 至少等待 10s
                return True
        return True

    def action_extract_multi_decision(self, ocr_reader):
        """
        截图并提取结构化决策 (V28 局部 ROI 加速版)
        """
        try:
            self._log("执行 ROI 局部扫描以提取决策...")
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = np.array(sct_img)
                
                # 仅分析屏幕右侧 60% 区域（避开侧边栏）
                h, w = img.shape[:2]
                roi = img[:, int(w*0.4):]
                
                results = ocr_reader.reader.readtext(roi)
                full_text = " ".join([r[1] for r in results])
                
                # 针对 V28 专家格式的增强匹配
                key_mapping = {
                    "overall": "Overall Preference",
                    "instruction": "Instruction Following",
                    "id": "ID Preservation",
                    "content": "Content Preservation",
                    "visual": "Visual Quality",
                    "generated": "Less AI Generated"
                }
                
                decision_map = {}
                import re
                for short_key, full_name in key_mapping.items():
                    # 匹配格式: "Overall: A" 或 "Overall Preference: Response B"
                    pattern = rf"{short_key}[:：\s]+(response\s*[ab]|both\s*good|both\s*bad|n/a|[ab])"
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        val = match.group(1).strip().upper()
                        if val == "A": val = "Response A"
                        if val == "B": val = "Response B"
                        decision_map[full_name] = val
                
                if decision_map:
                    self._log(f"解析成功: {decision_map}")
                    return decision_map
                return None
        except Exception as e:
            self._log(f"解析异常: {e}")
            return None

