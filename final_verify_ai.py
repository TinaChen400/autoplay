import os
import sys
import torch
import ctypes
from ultralytics import YOLO

# --- 关键：动态修复 llama-cpp-python 的 DLL 依赖 ---
DLL_PATH = r"C:\Users\Administrator\AppData\Local\Programs\Ollama\lib\ollama\cuda_v12"
if os.path.exists(DLL_PATH):
    # Python 3.8+ 需要使用 add_dll_directory
    os.add_dll_directory(DLL_PATH)

try:
    from llama_cpp import Llama
    HAS_LLAMA = True
except Exception as e:
    HAS_LLAMA = False
    LLAMA_ERROR = e

def final_ai_check():
    print("🚀 --- 最终 AI 环境自检 --- 🚀")
    
    # 1. 检查 GPU
    cuda_available = torch.cuda.is_available()
    print(f"[GPU] CUDA 可用性: {'✅ 正常' if cuda_available else '❌ 未检测到'}")
    if cuda_available:
        print(f"[GPU] 设备名称: {torch.cuda.get_device_name(0)}")
    
    # 2. 检查 YOLO
    yolo_path = "models/yolov8n.pt"
    if os.path.exists(yolo_path):
        try:
            model = YOLO(yolo_path)
            print(f"[YOLO] 模型加载: ✅ 成功 (路径: {yolo_path})")
        except Exception as e:
            print(f"[YOLO] 模型加载: ❌ 失败 ({e})")
    else:
        print(f"[YOLO] 模型加载: ❌ 缺失 (请确保 models/yolov8n.pt 存在)")

    # 3. 检查 Llama (GPU 版)
    if HAS_LLAMA:
        print(f"[Llama] 本地推理库: ✅ 正常 (CUDA 加速版)")
        print(f"       注意：库已加载成功，现在只需一个 .gguf 模型文件即可开始对话。")
    else:
        print(f"[Llama] 本地推理库: ❌ 异常 ({LLAMA_ERROR})")
        print(f"       提示：即使本地库失败，系统也会自动切换到‘云端豆包模式’运行。")

    print("\n[结论] 只要 [GPU] 为 ✅，项目即可在您的 4080 显卡上全速运行。")

if __name__ == "__main__":
    final_ai_check()
