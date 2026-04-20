# Task List V11 - DPI 逆向补偿与直接点击测试

- [ ] **Step 1: 渲染层反向缩放适配**
    - [ ] 在 `visual_dock_v2.py` 中引入 `pixel_scale = 1.5`。
    - [ ] 将所有 DWM 物理坐标除以 1.5 后再传递给 Qt 的 `setGeometry`。
- [ ] **Step 2: 直接点击测试脚本开发**
    - [ ] 创建 `scratch/direct_click_test.py`。
    - [ ] 绕过 UI 层，直接从底层驱动视觉寻锚与硬件点击，验证 V7 版算法。
- [ ] **Step 3: 最终冷启动与实测**
    - [ ] 清理残留进程，运行修正后的 V11 界面。
    - [ ] 运行直接点击测试，观察缩略图是否被点开。
- [ ] **Step 4: 归档总结**
    - [ ] 更新 `v11_walkthrough.md`。
