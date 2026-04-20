# Implementation Plan V12: 万能窗口吸附与快速启动集成

本计划旨在解决 Agent 切换窗口后失去目标的问题，并为用户提供极简的启动方式。

## 核心功能

1.  **万能吸附 (Space-to-Lock)**：
    *   在 `VisualDockV2` 中增加 **空格键** 交互逻辑。
    *   当用户处于 `[MANUAL]` 模式并将面板拖移至某窗口上方时，按空格键可强制将当前鼠标下的窗口锁定为任务目标（记住 HWND）。
2.  **快速启动脚本 (Start Shortcut)**：
    *   [NEW] [Start_HUD.bat](file:///d:/Dev/autoplay/Start_HUD.bat)：封装环境路径与运行指令，实现一键重启。
3.  **吸附逻辑优化**：
    *   引入 **HWND 持久化持锁**。一旦锁定，除非窗口关闭，否则不会因为标题改变（如切换标签页）而丢失。

## 变更内容

### 1. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 增加 HWND 锁定状态机。
- 实现 `keyPressEvent` 中的空格锁定逻辑。

### 2. [Shortcut Script] [NEW]
- 创建 `Start_HUD.bat`。

## 验证计划

1. **一键启动测试**：运行 `.bat` 文件，确认能正确开启 V11.1 稳定版界面。
2. **跨窗口吸附测试**：打开一个无关窗口（如记事本），拖动面板至其上方按空格，确认绿框能成功对齐非 Chrome 窗口。
