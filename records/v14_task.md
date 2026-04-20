# Task List V14 - 积木化工作流编辑器执行清单

- [ ] **Step 1: 技能引擎“原子化”重构**
    - [ ] 在 `MSISkills` 中提炼 `atomic_click_landmark`, `atomic_wait_visual`, `atomic_press_keys` 等底层接口。
- [ ] **Step 2: 任务持久化定义**
    - [ ] 创建 `config/missions.json` 初始模板。
    - [ ] 实现 `TaskBridge` 的动态任务解析功能。
- [ ] **Step 3: 指挥中心工作区升级**
    - [ ] 重构 `VisualDockV2` 侧边栏，支持动态增删卡片。
    - [ ] 实现每张卡片的“独立调试”逻辑。
- [ ] **Step 4: “图片打分”任务全流程搭建**
    - [ ] 使用新架构拼装用户语音描述的打分流程积木。
- [ ] **Step 5: 验证与交付**
    - [ ] 验证跨任务切换与积木重组的稳定性。
    - [ ] 编写 `v14_walkthrough.md`。
