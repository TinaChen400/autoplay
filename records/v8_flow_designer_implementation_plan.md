# Implementation Plan V8: 指挥中心增强 - 视觉流程设计师面板

本计划旨在为 `VisualDock`（HUD）增加一个侧边交互面板，允许用户可视化查看当前 Agent 的任务流程，并进行单步调试。

## UI 交互设计 (Rich Aesthetics)

1.  **设计语言**：
    *   **材质**：深色拟物化 + 玻璃拟态（Acrylic/Glassmorphism），背景带 30% 透明度。
    *   **布局**：在 HUD 的右侧增加一个可折叠的控制抽屉（Control Drawer）。
2.  **核心组件**：
    *   **Task List (任务链)**：以垂直列表形式展示当前 `msi_skills` 的执行序列（如：寻锚 -> 探测 -> 点击 -> 监控 -> 按键）。
    *   **Dashboard (调试台)**：
        *   `▶ Run Step`：仅运行当前高亮的一步。
        *   `↺ Reset`：重置任务状态机。
        *   `📸 Inspect`：强制抓拍当前画面并显示定位标识。

## 技术变更

### 1. [UI Core](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- **新增 `FlowControlPanel` 类**：继承自 `QFrame`，负责渲染流程列表。
- **主窗体布局调整**：使用 `QHBoxLayout` 承载“对位区”和“控制区”。

### 2. [Task Logic Middleware] [NEW]
- **新增 `src/execution/task_bridge.py`**：在 PyQt6 信号与 `MSISkills` 逻辑之间建立桥梁，支持“步进执行”。

## 验证计划

1. **布局验证**：启动 UI，确认侧边面板不会导致主窗口闪烁或对位偏移。
2. **调试验证**：在面板上点击 `Step Run`，确认远程桌面产生对应反馈。

---

## 待确认问题

> [!NOTE]
> 1. **宽度设置**：侧边面板默认宽度设为 300 像素是否合适？
> 2. **交互方式**：流程列表是仅供【查看】和【单步触发】，还是需要支持【拖拽排序】？（初期建议先实现查看与触发）。
