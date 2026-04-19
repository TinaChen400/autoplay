import mss
import numpy as np
import cv2
from typing import Optional, Dict

class VisionCapture:
    """
    负责实时视觉采集模块，基于 mss 实现高性能截屏。
    支持 OCR 懒加载，节省启动开销。
    """
    def __init__(self):
        self.sct = mss.mss()
        self.last_frame = None
        self._ocr = None # 懒加载标记

    def get_ocr(self):
        """仅在真正需要 AI 分析时才加载沉重的 OCR 引擎"""
        if self._ocr is None:
            from src.utils.ocr_reader import OCRReader
            self._ocr = OCRReader()
        return self._ocr

    def capture_screen(self, region: Optional[Dict[str, int]] = None) -> str:
        """
        截取屏幕并保存为临时图，返回路径。
        强制使用 D:\Dev\autoplay\temp 绝对路径。
        """
        import os
        import time
        
        # 强制 D 盘绝对路径
        temp_dir = r"D:\Dev\autoplay\temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        img_filename = f"capture_{int(time.time())}.jpg"
        img_path = os.path.join(temp_dir, img_filename)
        
        # 截取全屏
        sct_img = self.sct.grab(self.sct.monitors[1])
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # 保存
        img.save(img_path, quality=85)
        return img_path

# 补充缺失导入
from PIL import Image
