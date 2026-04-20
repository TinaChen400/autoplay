# Task List V13 - 终极对位与稳定性修复

- [ ] **Step 1: 升级对位逻辑 (DPI 归一化)**
    - [ ] 在 `VisualDockV2` 中引入 `self.screen().devicePixelRatio()`。
    - [ ] 彻底修正 `setGeometry` 的物理-逻辑单位换算。
- [ ] **Step 2: 颜色状态机统一**
    - [ ] 修改 `paintEvent`，由 `is_docked` 决定颜色，而非 `locked_hwnd`。
- [ ] **Step 3: 实现“死死纠缠”跟随逻辑**
    - [ ] 优化 `sync_logic`，确保窗口移动时绿框 0 延迟跟随。
- [ ] **Step 4: 冷启动与终极验证**
    - [ ] 杀死顽固进程，启动 V13。
    - [ ] 手动移动 Chrome 窗口，确认绿框不再掉队。
- [ ] **Step 5: 归档汇报**
    - [ ] 更新 `v13_walkthrough.md`。
