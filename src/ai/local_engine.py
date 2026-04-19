import requests
import json
from typing import Optional, Dict

class OllamaEngine:
    """
    基于 Ollama API 的本地大模型推理引擎。
    替代复杂的本地 llama-cpp-python 依赖，直接利用用户已有的高效 Ollama 环境。
    """
    def __init__(self, model_name: str = "llama3.1:8b", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.api_url = f"{host}/api/chat"

    def chat(self, prompt: str, system_prompt: str = "You are a helpful AI Agent.") -> Optional[str]:
        """
        发送对话请求到 Ollama。
        """
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False # 简化处理，不使用流式
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            print(f"Ollama 推理失败: {e}")
            return None

    def check_status(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

# 为了保持接口一致性，我们在 local_engine.py 中提供一个统一包装
class LocalAIEngine:
    def __init__(self, config: dict):
        # 优先从配置读取模型名称，默认为 llama3.1:8b
        model = config.get("model_name", "llama3.1:8b")
        self.engine = OllamaEngine(model_name=model)
        print(f"--- 本地 AI 引擎已初始化 (对接 Ollama: {model}) ---")

    def generate_workflow(self, task_desc: str, screen_context: str) -> Dict:
        """根据任务描述和视觉上下文生成工作流"""
        prompt = f"任务描述: {task_desc}\n视觉上下文 (OCR/识别结果): {screen_context}\n请生成结构化的工作流步骤。"
        response = self.engine.chat(prompt, system_prompt="你是一个远程桌面操作专家。")
        
        if response:
            return {"success": True, "workflow": response}
        return {"success": False, "msg": "本地推理异常"}
