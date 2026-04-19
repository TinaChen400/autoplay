import os
import sys
import json
import time
import pydirectinput

# Project path
sys.path.append(r"D:\Dev\autoplay")

def run_flick_scroll():
    print("--- EXEC: Physical Flick Scroll v2 ---")
    
    # 1. Load calibration
    db_path = r"D:\Dev\autoplay\config\calibration_db.json"
    if not os.path.exists(db_path):
        print("ERROR: calibration_db.json not found.")
        return
    
    with open(db_path, "r") as f:
        config = json.load(f)
    dock = config["dock_rect"]
    
    # 2. Target coordinates (Center of page)
    cx = dock["x"] + dock["width"] // 2
    sy = dock["y"] + (dock["height"] // 2) + 200 # Start lower
    ey = sy - 400                               # Drag up to scroll down
    
    print(f"PHYSICAL FLICK: hold at ({cx}, {sy}) for 500ms, then push to ({cx}, {ey})")
    print("Simulating in 2s, please hands off mouse...")
    time.sleep(2)
    
    # 3. Hardware-level execution
    pydirectinput.moveTo(cx, sy)
    pydirectinput.mouseDown()
    
    # Crucial dwell time for RDP focus
    time.sleep(0.5) 
    
    # Smooth step progression
    steps = 20
    for i in range(steps + 1):
        target_y = sy + int((ey - sy) * (i / steps))
        pydirectinput.moveTo(cx, target_y)
        time.sleep(0.04)
        
    time.sleep(0.3)
    pydirectinput.mouseUp()
    print("--- Flick Complete ---")

if __name__ == "__main__":
    run_flick_scroll()
