import os
import time
import io
import win32gui
import win32con
import win32api
import win32clipboard
import win32com.client
import pythoncom
from PIL import Image
import mss
import numpy as np
import cv2
import logging

logger = logging.getLogger("GPTOracle")

class GPTOracle:
    """
    GPT 决策引擎: 负责与浏览器中的 LLM (豆包/ChatGPT) 进行物理交互。
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPTOracle, cls).__new__(cls)
            cls._instance.records_dir = r"D:\Dev\autoplay\records"
            cls._instance.image_queue = []
            cls._instance.system_prompt = "请对以下截图进行专业分析。输出格式必须严格遵循协议：[维度名]: [选项] | 理由: [对比分析]"
            os.makedirs(cls._instance.records_dir, exist_ok=True)
        return cls._instance

    def __init__(self):
        # 属性已在 __new__ 中初始化
        pass

    def action_clear_queue(self):
        """清空待投喂图片队列"""
        self.image_queue = []
        logger.info("AI 图片队列已清空")
        return True

    def action_add_to_queue(self, rect):
        """抓取指定区域并加入投喂队列"""
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": int(rect["y"]),
                    "left": int(rect["x"]),
                    "width": int(rect["width"]),
                    "height": int(rect["height"])
                }
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                self.image_queue.append(img)
                logger.info(f"画面已加入 AI 队列 (当前长度: {len(self.image_queue)})")
                return True
        except Exception as e:
            logger.error(f"加入队列失败: {e}")
            return False

    def action_focus_gpt_window(self):
        """暴力聚焦浏览器窗口"""
        pythoncom.CoInitialize()
        try:
            candidates = []
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        t_lower = title.lower()
                        score = 0
                        if any(k in t_lower for k in ["chatgpt", "doubao", "豆包"]): score += 100
                        if any(k in t_lower for k in ["chrome", "edge", "browser"]): score += 10
                        if score > 0:
                            candidates.append((score, hwnd, title))
                return True

            win32gui.EnumWindows(callback, None)
            candidates.sort(key=lambda x: x[0], reverse=True)

            if not candidates:
                logger.warning("未找到匹配的浏览器窗口")
                return False

            target_hwnd = candidates[0][1]
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys('%') # 破除焦点锁定
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"激活 AI 窗口失败: {e}")
            return False
        finally:
            pythoncom.CoUninitialize()

    def action_send_queue_to_gpt(self, custom_prompt=None):
        """物理投喂：粘贴图片和提示词"""
        if not self.image_queue:
            logger.error("队列为空，无法投喂")
            return False

        try:
            # 1. 聚焦
            if not self.action_focus_gpt_window():
                return False

            # 2. 依次粘贴图片
            for i, img in enumerate(self.image_queue):
                self._put_img_to_clipboard(img)
                logger.info(f"正在粘贴第 {i+1} 张图片...")
                self._send_ctrl_key('V')
                time.sleep(2.0) # 等待上传

            # 3. 粘贴提示词
            prompt = custom_prompt if custom_prompt else self.system_prompt
            self._put_text_to_clipboard(prompt)
            logger.info("正在粘贴提示词...")
            self._send_ctrl_key('V')
            time.sleep(0.5)
            
            # 4. 发送 (Enter)
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            logger.info("AI 投喂任务已发送")
            return True
        except Exception as e:
            logger.error(f"投喂失败: {e}")
            return False

    def _send_ctrl_key(self, key):
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord(key.upper()), 0, 0, 0)
        win32api.keybd_event(ord(key.upper()), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

    def _put_img_to_clipboard(self, img):
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

    def _put_text_to_clipboard(self, text):
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
