import pyautogui
import time
import sys

def get_click_pos():
    print("\n>>>> [AGENT] 坐标捕获器已启动！")
    print(">>>> 请在 10 秒内，去点击一下远程页面中【那个白色的搜索框中心】。")
    print(">>>> 倒计时开始...")
    
    # 稍微等一下让用户切换窗口
    for i in range(10, 0, -1):
        # 实时检测鼠标状态（由于 python 监听全局点击较复杂，我们采用“移动并停留”或“5秒后记录当前位置”的简化策略）
        # 方案：等待 5 秒，记录 5 秒后鼠标所在的位置
        print(f"请将鼠标移到搜索框中心并停住！剩余时间: {i}s")
        time.sleep(1)
    
    x, y = pyautogui.position()
    print(f"\n>>>> [SUCCESS] 捕获成功！")
    print(f">>>> 真理坐标已锁定: ({x}, {y})")
    return x, y

if __name__ == "__main__":
    x, y = get_click_pos()
    # 将坐标保存，以便后续脚本读取
    import json
    with open(r"D:\Dev\autoplay\config\manual_calibration.json", "w") as f:
        json.dump({"x": x, "y": y}, f)
    print("坐标已存入 D 盘配置。")
