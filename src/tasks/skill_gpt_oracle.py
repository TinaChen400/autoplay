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

    def _log(self, msg):
        if self.bridge:
            self.bridge._log(f"[ORACLE] {msg}")
        else:
            print(f"[ORACLE] {msg}")

    def action_capture_to_clipboard(self, dock_rect):
        """
        捕获 Dock 窗口并放入 Windows 剪贴板 (CD_DIB)。
        """
        try:
            with mss.mss() as sct:
                # 调整为 mss 格式
                monitor = {
                    "top": int(dock_rect["y"]),
                    "left": int(dock_rect["x"]),
                    "width": int(dock_rect["width"]),
                    "height": int(dock_rect["height"])
                }
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # 将 PIL 转换为 DIB 格式放入剪贴板
                output = io.BytesIO()
                img.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:] # 剥离 14 字节的 BMP 文件头
                output.close()
                
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    self._log("截图已存入系统剪贴板 (Ready for Paste)")
                    return True
                finally:
                    win32clipboard.CloseClipboard()
        except Exception as e:
            self._log(f"截图至剪贴板失败: {e}")
            return False

    def action_focus_gpt_window(self):
        """
        寻找并激活包含 'ChatGPT' 字样的窗口 (加固版 V2)。
        """
        pythoncom.CoInitialize()
        try:
            target_hwnd = None
            candidates = []
            
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    # 拓宽搜索关键词：适配 ChatGPT、豆包 (Doubao)、Chrome 或 Edge 的各种标题状态
                    if any(k in title for k in ["chatgpt", "doubao", "豆包", "google chrome", "microsoft edge"]):
                        candidates.append(hwnd)
                return True

            win32gui.EnumWindows(callback, None)

            if not candidates:
                self._log("未找到任何浏览器窗口 (Chrome/Edge/ChatGPT)，请确保已打开浏览器")
                return False

            # 优先级排序：1. 含有 chatgpt/doubao 的窗口  2. 最近活跃的 Chrome/Edge 窗口
            target_hwnd = None
            priority_keywords = ["chatgpt", "doubao", "豆包"]
            for hwnd in candidates:
                t = win32gui.GetWindowText(hwnd).lower()
                if any(pk in t for pk in priority_keywords):
                    target_hwnd = hwnd
                    break
            
            if not target_hwnd:
                target_hwnd = candidates[0] # 取列表第一个作为保底

            try:
                # 强行破解焦点保护：发送 ALT 键信号
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
                
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(target_hwnd)
                win32gui.SetForegroundWindow(target_hwnd)
                time.sleep(1.0) 
                self._log(f"成功锁定并激活窗口: {win32gui.GetWindowText(target_hwnd)}")
                return True
            except Exception as e:
                self._log(f"聚焦窗口失败: {e}")
                return False
        finally:
            pythoncom.CoUninitialize()

    def _copy_text_to_clipboard(self, text):
        """
        将纯文本高效存入剪贴板 (Unicode 格式)。
        """
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            return True
        finally:
            win32clipboard.CloseClipboard()

    def action_send_to_gpt(self, custom_prompt=None):
        """
        在当前聚焦窗口执行 粘贴(图) + 粘贴(文) + 发送 (精密加固版 V27.7)。
        """
        try:
            prompt = custom_prompt if custom_prompt else self.system_prompt
            
            # --- 步骤 1: 粘贴图片 (图片已经在剪贴板里了，由 capture 步骤放入) ---
            pyautogui.hotkey('ctrl', 'v')
            self._log("已执行图片粘贴")
            time.sleep(2.0) # 留出图片解析时间
            
            # --- 步骤 2: 粘贴文字 (将提示词注入剪贴板并粘贴) ---
            if self._copy_text_to_clipboard(prompt):
                pyautogui.hotkey('ctrl', 'v')
                self._log(f"已执行提示词粘贴: {prompt[:15]}...")
            
            time.sleep(1.0)
            
            # --- 步骤 3: 强力发送 ---
            # 尝试回车
            pyautogui.press('enter')
            # 兼容性冗余：有些浏览器需要 Ctrl+Enter
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'enter')
            
            self._log("指令已成功投喂至 GPT 输入框并尝试发送")
            return True
        except Exception as e:
            self._log(f"发送指令失败: {e}")
            return False

    def action_extract_decision(self, ocr_reader):
        """
        截图 GPT/豆包 窗口并进行区域优化 OCR 查找最后的决策词 (V28.1)。
        """
        try:
            self._log("正在捕获屏幕并启动区域辅助 OCR...")
            
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = np.array(sct_img)
                # 转换为 RGB
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                
                # --- 区域优化: 只识别屏幕右侧 60% (LLM 聊天区) ---
                h, w = rgb_img.shape[:2]
                crop_x = int(w * 0.4) # 跳过左侧 40%
                cropped_img = rgb_img[:, crop_x:]
                
                # 保存一份裁剪后的快照供审计
                debug_path = os.path.join(self.records_dir, "gpt_decision_view.png")
                cv2.imwrite(debug_path, cv2.cvtColor(cropped_img, cv2.COLOR_RGB2BGR))
                
                self._log(f"OCR 正在扫描右侧区域 ({w-crop_x}px 宽)...")
                results = ocr_reader.reader.readtext(cropped_img)
                self._log(f"OCR 扫描完成，获得 {len(results)} 条文本片段")
                
                # 从下往上找最后的 A 或 B
                for i in range(len(results)-1, -1, -1):
                    text = results[i][1].upper()
                    # 极其宽松的匹配：包含 A 或 B 且长度极短
                    if 'A' in text and len(text) < 4: return "A"
                    if 'B' in text and len(text) < 4: return "B"
                
                self._log("未能在扫描区域内识别出明确决策 ('A' 或 'B')")
                return None
        except Exception as e:
            self._log(f"决策提取发生异常: {e}")
            return None
