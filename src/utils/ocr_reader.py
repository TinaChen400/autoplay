# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
import logging
import easyocr

logger = logging.getLogger("OCRReader")

class OCRReader:
    def __init__(self, use_gpu=True):
        try:
            # 基础初始化
            self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=use_gpu)
            logger.info(f"EasyOCR Engine Initialized (GPU: {use_gpu})")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.reader = None

    def read_screen(self, image):
        if self.reader is None: return []
        try:
            # 只做 2x 放大，不做二值化，保持图片原色（这对 EasyOCR 识别小字最稳）
            h, w = image.shape[:2]
            img_large = cv2.resize(image, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
            
            # 识别
            results = self.reader.readtext(img_large)
            
            formatted_results = []
            for (bbox, text, prob) in results:
                # 还原坐标 (除以 2)
                real_bbox = [[p[0]/2, p[1]/2] for p in bbox]
                formatted_results.append([real_bbox, text, prob])
            return formatted_results
        except Exception as e:
            logger.error(f"OCR reading failed: {e}")
            return []

    def find_largest_element(self, image, keyword):
        results = self.read_screen(image)
        if not results: return None
        import difflib
        best_match = {"score": 0, "pos": None}
        for bbox, text, prob in results:
            score = difflib.SequenceMatcher(None, keyword.lower(), text.lower()).ratio()
            if score > best_match["score"]:
                center_x = int((bbox[0][0] + bbox[1][0]) / 2)
                center_y = int((bbox[0][1] + bbox[2][1]) / 2)
                best_match = {"score": score, "pos": (center_x, center_y)}
        return best_match["pos"] if best_match["score"] > 0.5 else None
