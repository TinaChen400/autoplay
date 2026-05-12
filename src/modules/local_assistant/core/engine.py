import requests
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger("LocalAssistant.Engine")

class AssistantEngine:
    """
    专为 AI 助手优化的本地模型引擎。
    处理与 Ollama 的底层通信，支持系统提示词注入和超时控制。
    """
    def __init__(self, model_name: str = "llama3.2:1b", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.api_url = f"{host}/api/chat"

    def chat(self, user_prompt: str, system_prompt: str, **kwargs) -> Optional[str]:
        """
        发送结构化对话请求。
        """
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3, # 降低随机性，适合翻译和逻辑答复
                "num_predict": 512   # 限制输出长度
            }
        }
        
        try:
            logger.info(f"正在调用本地模型 {self.model_name}...")
            # 增加超时时间，避免 8b 模型加载太慢
            response = requests.post(self.api_url, json=payload, timeout=45)
            if response.status_code != 200:
                return f"Ollama 报错: {response.status_code}"
            result = response.json()
            content = result.get("message", {}).get("content", "").strip()
            if not content: return "模型返回了空消息"
            return content
        except requests.exceptions.Timeout:
            return "Ollama 推理超时 (模型加载太慢)"
        except Exception as e:
            logger.error(f"Ollama 推理失败: {e}")
            return f"连接失败: {str(e)}"

    def check_health(self) -> bool:
        """检查 Ollama 服务健康状态"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=3)
            return response.status_code == 200
        except:
            return False
