import cv2
import numpy as np
from typing import List, Optional, Tuple

class RecognitionExpert:
    """
    V4.2 识别专家系统 (The Oracle Group)
    支持多引擎回退机制：EasyOCR -> PaddleOCR -> YOLO -> Template
    """
    def __init__(self, vision_capture=None):
        self.vc = vision_capture
        self._paddle = None
        self._yolo = None

    def _get_easyocr(self):
        return self.vc.get_ocr()

    def _get_paddleocr(self):
        if self._paddle is None:
            try:
                from paddleocr import PaddleOCR
                # [V7.64] 极简初始化，移除 show_log 以兼容所有版本
                self._paddle = PaddleOCR(use_angle_cls=True, lang='ch')
            except Exception as e:
                print(f"[EXPERT] PaddleOCR Init Failed: {e}. Falling back to standard engine.")
                return None
        return self._paddle

    def find_landmark(self, img_np: np.ndarray, keywords: List[str], engines: List[str] = ["paddleocr", "easyocr"]) -> Optional[Tuple[int, int]]:
        """
        [V7.65] 异常隔离识别：确保任何引擎报错都不会导致主任务崩溃
        """
        for engine in engines:
            try:
                print(f"[EXPERT] Trying engine: {engine}")
                result = None
                
                if engine == "easyocr":
                    result = self._find_via_easyocr(img_np, keywords)
                elif engine == "paddleocr":
                    result = self._find_via_paddleocr(img_np, keywords)
                
                if result:
                    print(f"[EXPERT] Match found via {engine}: {result}")
                    return result
            except Exception as e:
                print(f"[EXPERT] Engine {engine} runtime error: {e}. Trying next...")
                continue
                
        return None

    def _find_via_easyocr(self, img_np: np.ndarray, keywords: List[str]):
        reader = self._get_easyocr().reader
        results = reader.readtext(img_np)
        for res in results:
            text = res[1].lower()
            if any(k.lower() in text for k in keywords):
                cx = int((res[0][0][0] + res[0][1][0]) / 2)
                cy = int((res[0][0][1] + res[0][2][1]) / 2)
                return (cx, cy)
        return None

    def _find_via_paddleocr(self, img_np: np.ndarray, keywords: List[str]):
        paddle = self._get_paddleocr()
        if not paddle: return None
        
        # [V7.65] 极简调用，移除 cls 参数
        results = paddle.ocr(img_np)
        if not results or not results[0]: return None
        
        for line in results[0]:
            text = line[1][0].lower()
            if any(k.lower() in text for k in keywords):
                bbox = line[0]
                cx = int((bbox[0][0] + bbox[1][0]) / 2)
                cy = int((bbox[0][1] + bbox[2][1]) / 2)
                return (cx, cy)
        return None
