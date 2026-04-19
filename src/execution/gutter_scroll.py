import os
import sys
import json
import time
import pydirectinput

sys.path.append(r"D:\Dev\autoplay")

def run_gutter_scroll():
    print("--- EXEC: Gutter-Click & Space Scroll v3 ---")
    
    # 1. 获取物理基座
    db_path = r"D:\Dev\autoplay\config\calibration_db.json"
    if not os.path.exists(db_path):
        print("ERROR: calibration_db.json not found.")
        return
    
    with open(db_path, "r") as f:
        config = json.load(f)
    dock = config["dock_rect"]
    
    # 2. 计算左侧页边距 (Gutter)
    # 通常网页左右两侧有 50-100 像素的空白
    gx = dock["x"] + 50
    gy = dock["y"] + dock["height"] // 2
    
    print(f"FOCUS ACTION: clicking at gutter ({gx}, {gy}) to reset browser focus...")
    print("Action in 2s, hands off mouse please...")
    time.sleep(2)
    
    # 3. 物理执行
    pydirectinput.click(gx, gy) # 点击空白处，把焦点从输入框拉出来
    time.sleep(0.5)
    
    print("SENDING PULSE: Spacebar x 2")
    # 空格键是网页下滑最强力的万能药
    pydirectinput.press('space')
    time.sleep(0.3)
    pydirectinput.press('space')
    
    print("--- Gutter Scroll Complete ---")

if __name__ == "__main__":
    run_gutter_scroll()
