import json
import requests
from src.ai.local_engine import LocalAIEngine

def test_ollama_integration():
    print("--- [Test] Ollama & Project Integration ---")
    
    # 模拟从配置加载
    with open('config/default_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    ai_config = config['ai']
    engine = LocalAIEngine(ai_config)
    
    # 测试简单对话
    print(f"Testing {ai_config['model_name']} to generate workflow...")
    result = engine.generate_workflow(
        task_desc="Click OK button",
        screen_context="Detect a dialog with 'OK' button at (960, 540)"
    )
    
    if result['success']:
        print("OK: AI response received:")
        print("-" * 30)
        print(result['workflow'])
        print("-" * 30)
    else:
        print(f"Error: {result.get('msg')}")

if __name__ == "__main__":
    test_ollama_integration()
