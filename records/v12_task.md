# Task List V12 - 万能吸附与快速启动实现

- [ ] **Step 1: 编写快速启动批处理脚本**
    - [ ] 创建 `Start_HUD.bat`。
- [ ] **Step 2: 实现在线窗口持锁逻辑**
    - [ ] 在 `VisualDockV2` 中引入 `self.locked_hwnd`。
    - [ ] 实现“空格键”获取当前面板下方窗口句柄的功能。
- [ ] **Step 3: 改造同步对位引擎**
    - [ ] 修改 `sync_logic`，优先追踪 `locked_hwnd`。
- [ ] **Step 4: 联调与验证**
    - [ ] 验证手动锁定记事本或普通网页的功能。
- [ ] **Step 5: 归档汇报**
    - [ ] 更新 `v12_walkthrough.md`。
