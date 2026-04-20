# Task List V6 - 物理级 DPI 修正与多引擎穿透执行

- [x] **Step 1: 核心库 DPI 感知增强**
    - [x] 在 `RemoteAgent` 中注入 `SetProcessDpiAwareness`。
- [x] **Step 2: 实施穿透式按键补丁**
    - [x] 在 `RemoteAgent` 中实现 `activate_window` 方法（含 Alt 脉冲激活）。
- [x] **Step 3: AHK 辅助引擎集成**
    - [x] 实现 `AHKControlSend` 备选路径。
- [/] **Step 4: 最终回归测试**
    - [ ] 执行全流程任务，确认大图交互效果。
- [ ] **Step 5: 归档成果**
    - [ ] 更新 `v6_walkthrough.md`。
