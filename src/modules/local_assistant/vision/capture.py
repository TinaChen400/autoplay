import logging
from typing import Optional, Dict
from src.vision.capture import VisionCapture

logger = logging.getLogger("LocalAssistant.Vision")

class ContextExtractor:
    """
    针对助手模块优化的上下文提取器。
    它不直接实现 OCR，而是利用底层的 VisionCapture 获取屏幕内容并转化为纯文本上下文。
    """
    def __init__(self):
        self.vc = VisionCapture()
        logger.info("ContextExtractor 初始化完成")

    def get_window_text(self, dock_rect: Optional[Dict[str, int]] = None) -> str:
        """
        获取指定窗口区域内的所有文字。
        dock_rect: {'x': x, 'y': y, 'width': w, 'height': h}
        """
        if not dock_rect:
            logger.warning("未提供窗口区域，将截取全屏")
            # 转换通用 rect 为 mss region 格式
            region = None
        else:
            region = {
                "left": int(dock_rect["x"]),
                "top": int(dock_rect["y"]),
                "width": int(dock_rect["width"]),
                "height": int(dock_rect["height"])
            }

        # 1. 截取图像
        img_np = self.vc.capture_region_np(region)
        if img_np is None:
            return ""

        # 2. 调用核心 OCR 引擎
        ocr = self.vc.get_ocr()
        results = ocr.get_detailed_results(img_np)
        
        # 3. 助手特有的后处理：按行排序并提取纯文本，忽略坐标
        # 按照 Y 坐标排序，模拟人类阅读顺序
        results.sort(key=lambda r: r[0][0][1]) 
        
        lines = [text for (bbox, text, prob) in results if prob > 0.2]
        return "\n".join(lines)
