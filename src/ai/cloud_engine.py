import os
import json
import base64
import requests
import urllib3
import ssl
from typing import Optional, Dict, List

# [V6.8] 禁用不安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
                    # [V6.11] 对齐 secrets.json 中的参数名
                    self.api_key = secrets.get("ark_api_key", "")
                    self.endpoint_id = secrets.get("doubao_endpoint_id", "")
            except:
                pass
                
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        
        # [V6.9] 创建增强型 Session，强制指定 SSL 协议版本
        self.session = requests.Session()
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context

        class TLSAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = create_urllib3_context()
                # [V6.10] 彻底关闭校验以绕过 SSL 协议冲突
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                context.set_ciphers('DEFAULT@SECLEVEL=1')
                kwargs['ssl_context'] = context
                return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

        self.session.mount("https://", TLSAdapter())

    def inference(self, prompt: str, images_b64: list = None) -> str:
        """执行视觉推理 (支持多图)"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        content = [{"type": "text", "text": prompt}]
        
        if images_b64:
            for img_b64 in images_b64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })
        
        messages = [{"role": "user", "content": content}]

        payload = {
            "model": self.endpoint_id,
            "messages": messages,
            "temperature": 0.1
        }

        try:
            import time
            for attempt in range(3):
                try:
                    # [V6.12] 极大延长超时时间至 120s，给视觉模型留足处理时间
                    response = self.session.post(
                        self.api_url, 
                        headers=headers, 
                        json=payload, 
                        timeout=120,
                        verify=False
                    )
                    res_data = response.json()
                    if 'choices' in res_data:
                        return res_data['choices'][0]['message']['content']
                    else:
                        return f"API_ERROR: {json.dumps(res_data)}"
                except Exception as e:
                    if attempt == 2: raise e
                    time.sleep(1)
        except Exception as e:
            import traceback
            return f"CONNECTION_ERROR: {str(e)}\n{traceback.format_exc()}"
