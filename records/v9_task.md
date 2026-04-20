# Task List V9 - DPI 物理像素对齐修复执行

- [ ] **Step 1: 物理坐标抓取模块重构**
    - [ ] 在 `window_lock.py` 中引入 `win32gui` 代替 `pygetwindow`。
    - [ ] 确保 `get_window_rect` 返回 100% 真实的物理像素。
- [ ] **Step 2: HUD 对齐算法修正**
    - [ ] 在 `visual_dock_v2.py` 中适配物理对位。
    - [ ] 增加 Windows 无形边框（Invisible Borders）补偿量。
- [ ] **Step 3: 锁定/解锁拖拽功能**
    - [ ] 实现拖拽时暂停自动吸附，防止“瞬移”回原位。
- [ ] **Step 4: 清理与环境重置**
    - [ ] 彻底杀死残留进程并冷启动 V9。
- [ ] **Step 5: 归档成果**
    - [ ] 更新 `v9_walkthrough.md`。
