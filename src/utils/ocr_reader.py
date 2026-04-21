import easyocr
import numpy as np
import cv2
import torch

class OCRReader:
    """
    基于 EasyOCR 的本地文字识别模块。
    利用 GPU (RTX 4080) 加速，为云端大模型提供精准的坐标字典。
    """
    def __init__(self, languages=['ch_sim', 'en']):
        # 自动检测 CUDA
        self.use_gpu = torch.cuda.is_available()
        print(f"--- OCR 引擎初始化 (GPU 加速: {self.use_gpu}) ---")
        # 首次初始化会下载模型，后续直接加载
        self.reader = easyocr.Reader(languages, gpu=self.use_gpu)

    def read_screen(self, image_np: np.ndarray) -> str:
        """
        全屏 OCR 扫描，返回结构化的文本位置上下文。
        """
        if image_np is None:
            return ""
        
        results = self.reader.readtext(image_np)
        
        context_lines = []
        for (bbox, text, prob) in results:
            if prob < 0.1: continue # 过滤极低置信度 (V27 调优版)
            
            # 计算中心点
            center_x = int(np.mean([p[0] for p in bbox]))
            center_y = int(np.mean([p[1] for p in bbox]))
            
            context_lines.append(f"文本: '{text}' | 坐标: ({center_x}, {center_y})")
            
        return "\n".join(context_lines)

    def find_largest_element(self, image_np: np.ndarray, target_text: str):
        """
        寻找所有匹配项中面积最大的那个（通常是 Logo 或主标题）。
        """
        results = self.reader.readtext(image_np)
        best_match = None
        max_area = 0
        
        for (bbox, text, prob) in results:
            if target_text.lower() in text.lower():
                # 计算矩形面积
                width = bbox[2][0] - bbox[0][0]
                height = bbox[2][1] - bbox[0][1]
                area = width * height
                
                if area > max_area:
                    max_area = area
                    center_x = int(np.mean([p[0] for p in bbox]))
                    center_y = int(np.mean([p[1] for p in bbox]))
                    best_match = (center_x, center_y)
                    
        return best_match
