import cv2
import numpy as np
from typing import List, Dict, Optional

class LayoutParser:
    """
    语义布局分割引擎 (V26: The Chameleon)
    V26 变色龙增强版：利用颜色空间分割 (Color Segmentation)。
    通过点击点的颜色倾向，反向寻找其所在的闭合组件。
    """
    @staticmethod
    def detect_color_block(image: np.ndarray, cx: int, cy: int) -> Optional[Dict]:
        """
        基于颜色相似度捕获点击点所在的 UI 块 (针对无边框设计)。
        """
        if image is None: return None
        
        # 1. 提取点击点的基准颜色
        # 获取中心点周围 5x5 的平均颜色，避免取到单个噪点
        roi = image[max(0, cy-2):cy+3, max(0, cx-2):cx+3]
        target_color = np.mean(roi, axis=(0,1)).astype(np.uint8)
        
        # 2. 颜色空间掩膜 (允许 20 度的灰度偏差)
        lower = np.clip(target_color.astype(np.int16) - 20, 0, 255).astype(np.uint8)
        upper = np.clip(target_color.astype(np.int16) + 20, 0, 255).astype(np.uint8)
        mask = cv2.inRange(image, lower, upper)
        
        # 3. 形态学闭合 (消除文字/图标空洞)
        kernel = np.ones((11, 11), np.uint8)
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 4. 轮廓提取
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_block = None
        min_dist_to_center = 9999
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # 必须包含中心点
            if x <= cx <= x + w and y <= cy <= y + h:
                # 过滤太小的块
                if w > 20 and h > 15:
                    return {
                        "id": 999, # V26 专属标识
                        "rect": (x, y, w, h),
                        "area": w * h
                    }
        return None

    @staticmethod
    def detect_blocks(image: np.ndarray) -> List[Dict]:
        """
        传统检测 (为了兼容性保留)
        """
        # V25 Otsu 逻辑
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = np.ones((7, 7), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        blocks = []
        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            if 400 < w*h:
                blocks.append({"id": i, "rect": (x, y, w, h), "area": w*h})
        return blocks

    @staticmethod
    def find_containing_block(blocks: List[Dict], px: int, py: int) -> Optional[Dict]:
        for block in blocks:
            bx, by, bw, bh = block["rect"]
            if bx <= px <= bx + bw and by <= py <= by + bh:
                return block
        return None
