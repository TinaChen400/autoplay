import cv2
import numpy as np
import logging

logger = logging.getLogger("LocalAssistant.Capture")

class ContextExtractor:
    def __init__(self, vc):
        self.vc = vc
        # [V22.40] 极速常驻：启动时即完成 OCR 热机，避免任务触发时重新加载
        from src.vision.ocr_reader import OCRReader
        self.reader = OCRReader()
        print("[CAPTURE] OCR 引擎已完成后台热机")

    def extract_context(self, dock_rect: dict):
        """
        [V22.31] 极速模式：PaddleOCR GPU 加速
        """
        import pyautogui
        import cv2
        import numpy as np
        import ctypes
        from PyQt6.QtWidgets import QApplication

        # 1. 物理转逻辑截图
        scale = ctypes.windll.user32.GetSystemMetrics(0) / QApplication.primaryScreen().size().width()
        lx, ly = int(dock_rect['x'] / scale), int(dock_rect['y'] / scale)
        lw, lh = int(dock_rect['width'] / scale), int(dock_rect['height'] / scale)

        screenshot = pyautogui.screenshot(region=(lx, ly, lw, lh))
        img_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        if img_np is None: return [], ""
        
        h, w = img_np.shape[:2]
        # 恢复 1280px 以确保文字识别精度 (RTX 4080 性能充足)
        target_w = 1280 
        scale_f = target_w / w
        img_np_resized = cv2.resize(img_np, (target_w, int(h * scale_f)))
        # 2. 稳定 OCR 模式 (使用常驻热机引擎)
        raw_items = []
        results = self.reader.get_detailed_results(img_np_resized)
        
        for (bbox, text, prob) in results:
            if prob > 0.15:
                x, y = int(bbox[0][0] / scale_f), int(bbox[0][1] / scale_f)
                w_box = int((bbox[1][0] - bbox[0][0]) / scale_f)
                h_box = int((bbox[2][1] - bbox[0][1]) / scale_f)
                if y > 80:
                    raw_items.append({"x": x, "y": y, "w": w_box, "h": h_box, "text": text})
        if not raw_items: return [], ""
        
        # --- 核心升级：物理胶水算法 (V22.35 强效降碎) ---
        raw_items.sort(key=lambda i: (i['y'], i['x']))
        merged_paragraphs = []
        if raw_items:
            current = raw_items[0]
            for next_item in raw_items[1:]:
                # 判断是否属于同一行或紧邻的段落 (垂直距离 < 1.5倍高度，水平有交集或靠得很近)
                y_dist = next_item['y'] - (current['y'] + current['h'])
                x_overlap = min(current['x'] + current['w'], next_item['x'] + next_item['w']) - max(current['x'], next_item['x'])
                
                # 如果垂直距离很近，且水平位置合理，则合并
                if y_dist < 12 and (x_overlap > -50): 
                    current['text'] += " " + next_item['text']
                    current['w'] = max(current['w'], next_item['x'] + next_item['w'] - current['x'])
                    current['h'] = next_item['y'] + next_item['h'] - current['y']
                else:
                    merged_paragraphs.append(current['text'])
                    current = next_item
            merged_paragraphs.append(current['text'])

        full_text = "\n\n".join(merged_paragraphs)
        return raw_items, full_text
