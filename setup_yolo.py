import os
from ultralytics import YOLO
import shutil

def download_yolo():
    print("正在下载 YOLOv8n 权重文件...")
    # 这会触发 ultralytics 的自动下载机制
    model = YOLO("yolov8n.pt")
    
    # 移动到项目指定的 models 文件夹
    target_path = "models/yolov8n.pt"
    if os.path.exists("yolov8n.pt"):
        shutil.move("yolov8n.pt", target_path)
        print(f"YOLO 权重已移动到: {target_path}")
    else:
        print("未在当前目录找到下载的文件，可能已在其他路径。")

if __name__ == "__main__":
    if not os.path.exists("models"):
        os.makedirs("models")
    download_yolo()
