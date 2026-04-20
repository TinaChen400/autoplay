# Implementation Plan V14: 多任务流引擎与图形化工作流架构

本计划将“指挥中心”重构为模块化、可切换的任务处理系统，支持您语音中提到的“图片识别与打分”等复杂业务流。

## 架构升级

1.  **任务抽象层 (Mission Abstraction)**：
    *   引入 `Mission` 类，每个任务拥有独立的名称、状态和 `TaskStep` 序列。
    *   实现 `TaskBridge` 的动态任务加载，支持从 JSON 或硬编码库中切换任务。
2.  **UI 任务导航栏 (Mission Selector)**：
    *   在 `VisualDockV2` 顶部增加任务页签或下拉列表。
    *   点击不同任务时，侧边栏卡片自动更新为该任务的步骤流。
3.  **复合技能扩展 (Skill Expansion)**：
    *   在 `MSISkills` 中新增支持复杂交互的原子动作：
        *   `wait_for_manual_confirm`: 等待用户在 HUD 上点击“确认”后再继续下一步。
        *   `sequential_click_probe`: 执行上下左右按键遍历不同图片。
        *   `spatial_locate_source`: 专门寻找“Source”地标进行精准对位。

## 任务示例：图片识别与打分流程

1.  **截屏自检**：调用底层快照。
2.  **锁定 Input**：点击关键词下方的缩略图。
3.  **等待大图**：视觉增量监测。
4.  **遍历打分**：执行 [Down, Right, Left, Up] 序列切换不同视图。
5.  **缩放交互**：执行鼠标滚轮或双击放大。

## 变更内容

### 1. [Task Bridge](file:///d:/Dev/autoplay/src/execution/task_bridge.py) [MODIFY]
- 支持多任务存储与切换逻辑。

### 2. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 增加任务切换按钮。
- 动态卡片渲染。

### 3. [MSISkills](file:///d:/Dev/autoplay/src/tasks/msi_skills.py) [MODIFY]
- 补充“遍历按键”、“手动确认等待”等高级函数。

## 验证计划

1. **任务切换测试**：点击“任务 A”与“任务 B”，确认侧边栏卡片内容即时更新。
2. **长流程跑通测试**：执行“图片打分”任务，观察 Agent 是否能按顺序完成 [截图 -> 找小图 -> 遍历方向键 -> 放大] 的全过程。
