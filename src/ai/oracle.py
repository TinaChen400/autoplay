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
        self.image_queue = []
        self.cached_hwnd = None
        # 默认提示词
        self.system_prompt = "这是Tina控制对象的实时截图。请根据任务要求分析并给出决策。只需返回答案本身（如 'A' 或 'B'）。"

    def action_clear_queue(self):
        """清空待投喂图片队列"""
        self.image_queue = []
        self._log("图片队列已清空")
        return True

    def action_add_to_queue(self, dock_rect):
        """抓取当前 Dock 区域并加入投喂队列"""
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": int(dock_rect["y"]),
                    "left": int(dock_rect["x"]),
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
        """[V33.0] 暴力对焦逻辑：强制置顶 + 标题全域匹配"""
        pythoncom.CoInitialize()
        try:
            candidates = []
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        t_lower = title.lower()
                        # 极其宽泛的匹配
                        score = 0
                        if any(k in t_lower for k in ["chatgpt", "doubao", "豆包"]): score += 100
                        if any(k in t_lower for k in ["chrome", "edge", "browser"]): score += 10
                        if score > 0:
                            candidates.append((score, hwnd, title))
                return True

            win32gui.EnumWindows(callback, None)
            # 按分值排序
            candidates.sort(key=lambda x: x[0], reverse=True)

            if not candidates:
                print("[ORACLE] 警告: 未找到任何匹配的浏览器窗口")
                return False

            print(f"[ORACLE] 发现候选窗口 ({len(candidates)} 个):")
            for s, h, t in candidates[:3]:
                print(f"  - [Score:{s}] HWND:{h} Title: {t}")

            target_hwnd = candidates[0][1]
            
            try:
                # 暴力置顶三部曲
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%') # 破解焦点锁定
                
                # 尝试解除最小化并置顶
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(target_hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                win32gui.SetForegroundWindow(target_hwnd)
                
                # 瞬间取消最前端属性（避免遮挡后续操作），但保留焦点
                time.sleep(0.1)
                win32gui.SetWindowPos(target_hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                
                time.sleep(0.5)
                return True
            except Exception as e:
                print(f"[ORACLE] 激活窗口失败: {e}")
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

    def action_send_queue_to_gpt(self, custom_prompt=None):
        """[V32.7] 工业级投喂逻辑：使用 win32api 注入按键 + 智能等待"""
        import win32api, win32con, time
        if not self.image_queue:
            self._log("错误: 队列为空，无可投喂内容")
            return False

        def send_ctrl_key(key):
            """底层注入 Ctrl + Key"""
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(ord(key.upper()), 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(ord(key.upper()), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.1)

        try:
            # 1. 批量粘贴图片
            for i, img in enumerate(self.image_queue):
                self._put_img_to_clipboard(img)
                print(f"  - [Oracle] 正在粘贴第 {i+1} 张图片...")
                send_ctrl_key('V')
                time.sleep(2.0) # 延长图片上传缓冲时间

            # 2. 注入提示词
            prompt = custom_prompt if custom_prompt else self.system_prompt
            if self._copy_text_to_clipboard(prompt):
                print(f"  - [Oracle] 正在粘贴提示词...")
                send_ctrl_key('V')
                time.sleep(0.8)
            
            # 3. 强力发送 (Enter + Ctrl+Enter 双重补弹)
            print(f"  - [Oracle] 正在执行发送指令...")
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            time.sleep(0.5)
            send_ctrl_key('\r') # 发送 Ctrl+Enter
            
            self._log("全量图片与指令已通过底层驱动投喂完毕")
            return True
        except Exception as e:
            self._log(f"投喂失败: {e}")
            return False

    def action_send_to_gpt(self, custom_prompt=None):
        """兼容旧版：发送指令"""
        # 如果队列为空，则尝试传统的 capture -> send 流程（虽然现在建议用 queue）
        if not self.image_queue:
            return self.action_send_queue_to_gpt(custom_prompt)
        return self.action_send_queue_to_gpt(custom_prompt)

    def _put_img_to_clipboard(self, img):
        """将 PIL Image 存入剪贴板"""
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
