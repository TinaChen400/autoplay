# Tina 视觉自动化坐标对位标准化准则 (V22.1 物理核心版)

## 1. 核心底盘标准 (The Gold Standard)
所有坐标计算必须基于**物理像素 (Physical Pixels)**，绝对禁止使用逻辑像素。
- **DPI 感知**：所有入口文件（如 `main.py`, `visual_dock.py`）必须注入以下代码以穿透系统缩放：
  ```python
  try:
      import ctypes
      ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
  except:
      ctypes.windll.user32.SetProcessDPIAware()
  ```
- **标准宽度**：Tina 远程窗口的物理宽度必须强制锁定为 **1491 px** (这是确保 X 轴偏移量生效的前提)。
- **参考高度**：高度通常锁定为 **900 px**。

## 2. 坐标原点 (Origin)
- **唯一原点**：坐标计算的 `(0,0)` 起始点必须是 `config/calibration_db.json` 文件中 `dock_rect` 的 `x` 和 `y`。
- **同步机制**：技能执行前必须通过 `ViewportManager` 获取最新的 `dock_rect`。严禁写死屏幕绝对坐标。

## 3. 混合对位逻辑 (Hybrid Mapping)
- **Y 轴 (行定位)**：使用 OCR 动态识别行标题（如 "Overall Preference"），提取其物理中心 Y 坐标。
- **X 轴 (列定位)**：**严禁使用 OCR 识别按钮**。必须使用以下基于 1491 物理宽度测得的固定偏移量：
    - **Response A**: `+1249`
    - **Response B**: `+1341`
    - **Both Good**: `+1433`
    - **Both Bad**: `+1507`
- **计算公式**：`实际点击 X = 窗口物理左边界(x) + 固定偏移量`

## 4. 开发与维护守则
- **禁止魔法数字**：禁止在代码中手动通过 `* 1.25` 或 `/ 1.5` 这种硬编码比例来修复缩放问题。开启 DPI 感知后，比例永远是 1:1。
- **对齐校验**：若怀疑对位偏移，必须运行 `detect_actual_window_dpi.py` 观察红色扫描线是否精准垂直穿过单选按钮中心。
- **环境变更**：若窗口物理尺寸（Width）发生不可避的变动，必须同步更新本准则中的第 3 条偏移量字典。

---
> **备忘录**：本准则于 2026-04-30 讨论通过并强制执行。未来任何关于视觉识别、屏幕对齐、鼠标点击的修改，必须以此流程为准。
