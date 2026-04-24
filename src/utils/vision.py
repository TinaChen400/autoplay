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
        截取屏幕或特定区域并保存。区域格式: {'top': x, 'left': y, 'width': w, 'height': h}
        强制使用 D:\Dev\autoplay\temp 绝对路径。
        """
        import os
        import time
        from PIL import Image
        import mss
        
        temp_dir = r"D:\Dev\autoplay\temp"
        os.makedirs(temp_dir, exist_ok=True)
            
        img_filename = f"capture_{int(time.time())}.jpg"
        img_path = os.path.join(temp_dir, img_filename)
        
        # 截取逻辑
        with mss.mss() as sct:
            if region:
                # 针对高分屏优化的区域截取
                sct_img = sct.grab(region)
            else:
                # 默认获取主显示器
                sct_img = sct.grab(sct.monitors[1])
                
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(img_path, quality=85)
        return img_path

    def compare_images(self, path1: str, path2: str) -> float:
        """
        比较两张图片的差异度。返回差异百分比 (0.0 - 100.0)。
        """
        img1 = cv2.imread(path1)
        img2 = cv2.imread(path2)
        
        if img1 is None or img2 is None:
            return 100.0
            
        if img1.shape != img2.shape:
            # 尺寸不一致，强制缩放对齐
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
        # 计算绝对差值
        diff = cv2.absdiff(img1, img2)
        non_zero_count = np.count_nonzero(diff)
        total_pixels = img1.size
        
        diff_percent = (non_zero_count / total_pixels) * 100
        return diff_percent

# 补充缺失导入
from PIL import Image
