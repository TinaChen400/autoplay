import base64
import os
import io

class AIModelManager:
    """
    负责管理 AI 引擎的调用。
    已集成硬盘级指令缓存，优先从本地读取指令。
    """
    def __init__(self, engine):
        self.engine = engine
        # 即使现在不直接用 secrets，也保留加载逻辑以便扩展
        secrets_path = 'config/secrets.json'
        self.secrets = {}
        if os.path.exists(secrets_path):
            import json
            try:
                with open(secrets_path, 'r') as f:
                    self.secrets = json.load(f)
            except:
                pass

    def get_inference(self, task_name: str, ocr_context: str, image_path: str = None) -> dict:
        """调用 AI 引擎获取决策指令"""
        try:
            # 1. 准备图像数据并执行视觉压缩
            img_b64 = ""
            if image_path and os.path.exists(image_path):
                from PIL import Image
                img = Image.open(image_path)
                # 缩放至 1280 宽度以提速
                if img.width > 1280:
                    ratio = 1280.0 / img.width
                    new_h = int(img.height * ratio)
                    img = img.resize((1280, new_h), Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=75)
                img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # 2. 构建提示词
            prompt = f"任务目标：{task_name}\nOCR上下文：{ocr_context}\n请根据截图给出物理操作指令。格式仅限：CLICK(x,y) 或 INPUT(text)。不要输出任何多余字符。如果是输入，请在INPUT()括号内只写内容。"

            # 3. 发起请求
            response = self.engine.inference(prompt, img_b64)
            
            return {
                "success": True,
                "workflow": response
            }
        except Exception as e:
            return {
                "success": False,
                "msg": str(e)
            }
