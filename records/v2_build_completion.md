# 远程桌面视觉 AI Agent 项目执行记录 - v2

**执行日期**：2026-04-19
**版本号**：v2
**状态**：完成核心构建 / 待环境联调

## 已完成的构建内容
1. **环境初始化**：
    - 创建了基于 D 盘的 `.venv` 虚拟环境。
    - 生成了 `requirements.txt` 并完成了大部分依赖安装（注：Llama-cpp 本地编译失败，系统已预留云端豆包模型作为 Fallback）。
2. **核心工具类**：
    - `src/utils/vision.py`: 基于 mss 的毫秒级截屏。
    - `src/utils/window_lock.py`: 远程窗口（向日葵等）多关键字句柄锁定与坐标同步。
3. **PyQt6 透明控制台**：
    - `src/overlay/overlay_window.py`: 实现透明、置顶、穿透窗口。
    - `src/overlay/ui_panels.py`: 实现任务列表、资源监控日志、工作流审批弹窗。
4. **AI 与执行逻辑**：
    - `src/ai/model_manager.py`: 本地/云端双模自动切换架构。
    - `src/execution/ahk_executor.py`: AHK 模拟点击、输入及“页面清空”功能。
    - `src/execution/task_machine.py`: 任务状态机控制循环逻辑。
5. **集成入口**：
    - `main.py`: 实现 UI、视觉监听与坐标同步的完整集成。

## 待优化与已知问题
- **本地推理加速**：`llama-cpp-python` 需要在具备 C++ 编译环境的机器上安装后方可实现 GPU 4-bit 加速，当前采用 Mock/Cloud 模式验证流程。
- **AHK 路径**：默认指向 `C:\Program Files\AutoHotkey\AutoHotkey.exe`，已在 `config/default_config.json` 中配置。

## 下一步建议
1. 运行 `main.py` 在向日葵/远程窗口上进行透明层贴合测试。
2. 配置 `.env` 中的云端 API Key 激活全流程 AI 决策。
