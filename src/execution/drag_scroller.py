import os
import sys
import json
import time
import pydirectinput

sys.path.append(r"D:\Dev\autoplay")

def run_drag_scroll():
    print("--- 启动【物理对位：强力拖拽下滑】 ---")
    
    # 1. 寻找物理基座 (绿框边缘)
    db_path = r"D:\Dev\autoplay\config\calibration_db.json"
    if not os.path.exists(db_path):
        print("错误: 未找到对齐底座")
        return
    
    with open(db_path, "r") as f:
        config = json.load(f)
    dock = config["dock_rect"]
    
    # 2. 定位滚动条理论区域 (靠近右侧边缘)
    # 计算绿框右侧减去 25 像素 (通常是滚动条所在位置)
    scrollbar_x = dock["x"] + dock["width"] - 25
    start_y = dock["y"] + 200 # 从上方一点开始抓
    end_y = start_y + 400     # 向下拉动 400 像素
    
    print(f"PHYSICAL SIM: mouseDown at ({scrollbar_x}, {start_y}), drag to ({scrollbar_x}, {end_y})")
    print("准备模拟拖动，请离手鼠标 (2s 倒计)...")
    time.sleep(2)
    
    # 3. 物理执行
    # pydirectinput 的 mouseDown 是硬件级的
    pydirectinput.moveTo(scrollbar_x, start_y)
    pydirectinput.mouseDown()
    time.sleep(0.2)
    
    # 平滑拖拽，分 10 步完成，模拟人类动作
    steps = 10
    for i in range(steps + 1):
        target_y = start_y + int((end_y - start_y) * (i / steps))
        pydirectinput.moveTo(scrollbar_x, target_y)
        time.sleep(0.05)
        
    time.sleep(0.2)
    pydirectinput.mouseUp()
    print("--- 物理拖拽指令已完成！ ---")

if __name__ == "__main__":
    run_drag_scroll()
