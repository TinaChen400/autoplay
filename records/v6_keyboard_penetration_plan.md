# Implementation Plan V6: 驱动级按键穿透与 AHK 备选方案

本计划旨在解决即使在双击和长按后依然无法在远程桌面触发按键的问题。我们将引入底层 AHK 模拟并进行多引擎交叉验证。

## 修复策略

1.  **增加 AHK 驱动支持**：
    *   在 `RemoteAgent` 中集成 AHK 脚本调用。AHK 能够发送更底层的 ScanCode，且支持控制特定窗口句柄，穿透力优于 Python 库。
2.  **多引擎混合压力测试**：
    *   编写测试脚本，依次使用 `pydirectinput` (ScanCode模式)、`pyautogui` (虚拟按键模式) 和 `AHK` 对当前窗口发送方向键。
3.  **焦点与点击优化**：
    *   尝试在按键前发送 `Alt+Tab` 或 `Esc`（非破坏性按键）来激活远程端的输入流通道。

## 变更内容

### 1. [RemoteAgent](file:///d:/Dev/autoplay/src/execution/remote_agent.py)
- **新增 `press_key_via_ahk(keys)`**：利用 subprocess 调用 AHK 引擎执行按键。

### 2. [Debug Tool](file:///d:/Dev/autoplay/scratch/test_penetration.py) [NEW]
- 创建一个专门的穿透测试脚本，记录每种方式的执行结果。

## 验证计划

1. **可视化验证**：我会运行混合测试，请您观察哪种方式触发了照片的翻页或位移。
2. **全量集成**：将验证成功的最强引擎集成进 `msi_skills.py`。
