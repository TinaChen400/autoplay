import torch
from ultralytics import YOLO
try:
    from llama_cpp import Llama
    HAS_LLAMA = True
except ImportError:
    HAS_LLAMA = False
import os

def check_ai():
    print("=== AI 环境自检 ===")
    
    # 1. 检查 CUDA
    cuda_available = torch.cuda.is_available()
    print(f"[GPU] CUDA 可用性: {cuda_available}")
    if cuda_available:
        print(f"[GPU] 当前显卡: {torch.cuda.get_device_name(0)}")
    
    # 2. 检查 YOLO
    yolo_path = "models/yolov8n.pt"
    if os.path.exists(yolo_path):
        try:
            model = YOLO(yolo_path)
            print(f"[YOLO] 模型加载成功: {yolo_path}")
        except Exception as e:
            print(f"[YOLO] 加载失败: {e}")
    else:
        print(f"[YOLO] 未找到模型文件: {yolo_path}")
        
    # 3. 检查 Llama 接口与显卡加速
    if HAS_LLAMA:
        print("[Llama] llama-cpp-python 安装状态: 已安装")
        # 尝试检查是否支持 GPU (通过尝试初始化一个小量级参数)
        # 注意：没有模型文件无法真正测试推理，但可以检查库构建信息
        try:
            # 这是一个简单的库检查，不涉及模型加载
            import llama_cpp
            print(f"[Llama] 库版本: {llama_cpp.__version__}")
        except Exception as e:
            print(f"[Llama] 库运行异常: {e}")
    else:
        print("[Llama] llama-cpp-python 安装状态: 未安装")

if __name__ == "__main__":
    check_ai()
