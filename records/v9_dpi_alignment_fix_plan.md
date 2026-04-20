# Implementation Plan V9: 150% 缩放下的 DPI 全链路物理对齐

本计划旨在解决高 DPI 环境下（用户当前为 150% 缩放）指挥中心边框过大、对位偏离以及无法手动挪动的问题。

## 修复策略

1.  **物理坐标统一化**：
    *   废弃 `pygetwindow` 的逻辑像素获取，改用 `win32gui.GetWindowRect` 直接读取 Windows 底层的物理像素坐标。
    *   确保 `VisualDockV2` 窗口在启动之初就锁定在物理像素模式。
2.  **吸附逻辑优化**：
    *   **解耦移动逻辑**：增加一个“锁定/解锁”状态。当用户尝试手动拖拽时，Agent 自动暂停吸附，允许用户自定义位置。
    *   **对齐修正**：增加 -8 像素的窗口边框修正常数（Windows 11 隐形边框补偿）。
3.  **可视化校验**：
    *   在面板上实时显示当前的 DPI 缩放系数和物理坐标值，方便排查。

## 变更内容

### 1. [Window Lock Utility](file:///d:/Dev/autoplay/src/utils/window_lock.py) [MODIFY]
- 使用 `win32gui` 重写 `get_window_rect`，确保返回的是原始物理坐标。

### 2. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 引入 `DPIAware` 计算公式。
- 实现拖拽保护逻辑。

## 验证计划

1. **冷启动测试**：清理进程后启动，确认绿框不再“虚大”。
2. **拖拽测试**：确认点击右侧面板时可以手动挪动窗口。
