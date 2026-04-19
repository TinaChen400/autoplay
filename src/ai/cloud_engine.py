import os
import json
import base64
import requests
from typing import Optional, Dict, List

class DoubaoAIEngine:
    """
    对接火山引擎豆包 (Doubao) Seed-1.8 视觉大模型引擎。
    已集成密钥自加载逻辑。
    """
    def __init__(self):
        # 自动加载密钥与端点
        secrets_path = 'config/secrets.json'
        self.api_key = ""
        self.endpoint_id = ""
        
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                    self.api_key = secrets.get("cloud_api_key", "")
                    self.endpoint_id = secrets.get("endpoint_id", "ep-20240604011832-6p2j4") # 默认值
            except:
                pass
                
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    def inference(self, prompt: str, image_b64: str = "") -> str:
        """执行视觉推理"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        if image_b64:
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
            })

        payload = {
            "model": self.endpoint_id,
            "messages": messages,
            "temperature": 0.1
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            res_data = response.json()
            return res_data['choices'][0]['message']['content']
        except Exception as e:
            return f"ERROR: {str(e)}"
