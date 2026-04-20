# Implementation Plan V5: 远程桌面按键穿透与焦点增强

本计划旨在解决 V4 版本中按键序列未生效的问题，通过物理双击、增加按键时长以及底层 ScanCode 模拟来确保动作触达。

## 修复策略

1.  **焦点加固**：
    *   将原本的单次点击改为 **物理双击 (Double Click)**，强制捕获大图图层的 JS Focus。
    *   点击后增加 1.0s 的静态等待，确保焦点状态在远程端同步。
2.  **按键拟真处理**：
    *   放弃 `press()` 方法（该方法按键极快，易被远程桌面过滤）。
    *   采用 `keyDown()` -> `sleep(0.1)` -> `keyUp()` 的组合，模拟真实的物理按压感。
3.  **备选驱动方案**：
    *   如果 `pydirectinput` 依然被过滤，将尝试调用项目中已有的 `AHK` 执行器，利用系统级钩子进行穿透。

## 变更内容

### 1. [RemoteAgent](file:///d:/Dev/autoplay/src/execution/remote_agent.py)
- **优化 `press_key_sequence`**：改为 `keyDown/keyUp` 模式，并增加 `hold_time` 参数。

### 2. [MSISkills](file:///d:/Dev/autoplay/src/tasks/msi_skills.py)
- **优化 `interact_with_large_image`**：
    - 将中心点点击改为 `doubleClick`。
    - 增加焦点等待时长。

## 验证计划

1. **单步验证**：单独运行按键测试脚本，观察远程窗口是否有反应。
2. **全周期验证**：重新运行 `msi_skills.py`，确认在大图弹开后，能够看到图片产生位移或对应的按键效果。
