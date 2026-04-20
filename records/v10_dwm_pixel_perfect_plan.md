# Implementation Plan V10: DWM 像素级视觉对齐与吸附增强

本计划旨在通过 DWM（桌面窗口管理器）的底层属性，消除 10 像素的隐形边框干扰，实现指挥中心与远程桌面的极致对位。

## 修复策略

1.  **DWM 属性直连**：
    *   在 `window_lock.py` 中引入 `dwmapi.dll` 调用。
    *   使用 `DWMWA_EXTENDED_FRAME_BOUNDS` 属性获取窗口的“纯视觉边界”，绕过 Win32 带阴影的脏数据。
2.  **绝对坐标系同步**：
    *   确保 `VisualDockV2` 的对位逻辑与 DWM 抓取的可见边界 1:1 同步。
3.  **吸附鲁棒性**：
    *   增加对 `DWM` 重绘事件的实时监听，确保在窗口缩放时绿框能瞬间“咬紧”。

## 变更内容

### 1. [Window Lock Utility](file:///d:/Dev/autoplay/src/utils/window_lock.py) [MODIFY]
- 改用 `ctypes.windll.dwmapi` 获取物理对位参数。

### 2. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 同步适配 DWM 坐标系。

## 验证计划

1. **像素对等测试**：启动后确认绿框的左上角与缩略图窗口的左上角重合度达到 100%。
