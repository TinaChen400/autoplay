# Task List V11.1 - 指挥中心复活与异步大脑集成

- [ ] **Step 1: UI 异步化重构**
    - [ ] 移除 `__init__` 中的同步 `TaskBridge` 加载。
    - [ ] 实现 `lazy_init_brain` 方法，由 `QTimer` 触发。
- [ ] **Step 2: 鲁棒性增强**
    - [ ] 在 `sync_logic` 中增加全局异常捕获。
    - [ ] 在 `__main__` 中增加 `traceback` 日志持久化。
- [ ] **Step 3: 环境重置与复活测试**
    - [ ] 强制清除 `python.exe` 进程。
    - [ ] 运行 V11.1，确认界面能在 1 秒内弹出。
- [ ] **Step 4: 归档汇报**
    - [ ] 更新 `v11_1_walkthrough.md`。
