# Implementation Plan V11.1: 指挥中心复活补丁

本计划旨在修复 V11 指挥中心死联、崩溃无法启动的问题。

## 修复策略

1.  **异步大脑初始化 (Async Brain Load)**：
    *   移除 `__init__` 中同步加载 `TaskBridge` 的逻辑（这会导致 UI 初始化超时或 DLL 冲突）。
    *   改用 `QTimer.singleShot` 在 UI 显示后 1 秒再启动 `TaskBridge`。
2.  **健壮性对位**：
    *   在 `sync_logic` 中增加全局异常捕获，确保即使坐标抓取失败也不会导致整个程序退出。
3.  **零延迟捕获 (Crash Guard)**：
    *   在 `main` 函数中使用 Python 标准 `traceback` 将错误输出到本地文件，确保即使秒退也能看到原因。

## 变更内容

### 1. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 改造为延迟加载模式。

## 验证计划

1. **界面启动测试**：运行脚本后，UI 应在 1 秒内弹出，不受 AI 模型加载影响。
2. **功能自愈测试**：等待模型加载完成后，任务卡片灯自动亮起。
