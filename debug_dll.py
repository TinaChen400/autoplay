import os
import ctypes
import sys

def debug_dll_load():
    dll_path = r"D:\Dev\autoplay\.venv\lib\site-packages\llama_cpp\lib\llama.dll"
    print(f"尝试手动加载: {dll_path}")
    
    # 尝试设置 DLL 搜索目录（针对本地 CUDA 等）
    # 常见的 CUDA 安装路径
    cuda_path = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin"
    if os.path.exists(cuda_path):
        print(f"发现 CUDA 12.4 路径，尝试添加到 DLL 目录: {cuda_path}")
        os.add_dll_directory(cuda_path)
    
    try:
        # 使用 ctypes 尝试加载并获取错误码
        handle = ctypes.WinDLL(dll_path)
        print("成功！DLL 已加载。")
    except Exception as e:
        print(f"失败！错误信息: {e}")
        print("\n这通常意味着以下原因之一：")
        print("1. 缺少 Microsoft Visual C++ Redistributable (2015-2022)")
        print("2. 缺少 CUDA Runtime DLL (如 cudart64_12.dll)")
        print("3. 显卡驱动版本不兼容（但您是 560.94，应该没问题）")

if __name__ == "__main__":
    debug_dll_load()
