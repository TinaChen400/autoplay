# Task List V10 - DWM 像素级对齐执行清单

- [ ] **Step 1: 核心坐标引擎升级**
    - [ ] 在 `window_lock.py` 中引入 `ctypes.windll.dwmapi`。
    - [ ] 实现 `get_real_physical_rect` 替换旧的对位逻辑。
- [ ] **Step 2: HUD 指挥中心适配**
    - [ ] 在 `visual_dock_v2.py` 中同步使用 DWM 物理边界。
    - [ ] 确保 `overlay_area` 的尺寸与 DWM 可见像素完全一致。
- [ ] **Step 3: 最终清理与环境冷启动**
    - [ ] 强制清除所有 python.exe 残留。
    - [ ] 启动 V10 回归测试。
- [ ] **Step 4: 归档与反馈**
    - [ ] 更新 `v10_walkthrough.md`。
