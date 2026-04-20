# Implementation Plan V6: 物理级 DPI 修正与多引擎穿透

本计划旨在解决由于 DPI 缩放导致的点击偏离，以及远程桌面环境下按键被拦截的深度问题。

## 修复策略

1.  **DPI 同步化 (DPI Sync)**：
    *   在测试脚本中引入 `ctypes.windll.shcore.SetProcessDpiAwareness(1)`。
    *   确保所有坐标计算均基于“物理像素”，与 HUD（指挥中心）保持一致，纠正点击偏离风险。
2.  **多引擎火力测试**：
    *   **方案 A (ScanCode)**：使用 `win32api.keybd_event` 并手动映射硬件扫描码。
    *   **方案 B (Message Injection)**：尝试使用 `win32api.PostMessage` 直接向窗口句柄投递按键消息，绕过输入流拦截。
    *   **方案 C (AHK ControlSend)**：利用现有的 AHK 执行器，向后台窗口注入动作。
3.  **视觉反馈检测**：
    *   在每次按键后进行微型截图对位，观察 `diff` 变化，自动确认哪种引擎生效。

## 变更内容

### 1. [Test Tool] [scratch/v6_deep_test.py](file:///d:/Dev/autoplay/scratch/v6_deep_test.py) [NEW]
- 包含 DPI 感知和三种模拟引擎的对比测试脚本。

## 待确认问题

> [!IMPORTANT]
> 1. 您是否可以配合在脚本执行时，手动点击一次大图？这样我可以排除“JS 焦点未加载”的干扰。
