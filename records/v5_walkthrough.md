# Walkthrough V5: 远程按键穿透与焦点增强成功

本版本通过物理级仿真，彻底解决了远程环境中按键信号被过滤或焦点丢失的问题。

## 重要修复参数

1.  **物理双击 (Focus Capture)**：
    - 在按键前执行 `double_click_at` 中心点，强制捕获远程图层的 JS 焦点。
2.  **长按模拟 (Key Holding)**：
    - 将按键逻辑改为 `keyDown` -> `0.15s delay` -> `keyUp`。
    - 这种时长（Hold Time）能够有效通过远程桌面协议的信号校验。
3.  **多路径定位 (Robust OCR)**：
    - 兼容了 `SOURCE` / `INPUT` / `OUTPUT` 多种业务地标，极大提升了脚本在不同页面状态下的生存能力。

## 执行数据

- **触发锚点**: `SOURCE`
- **视觉判定**: 34.75% 像素面积增量。
- **Focus 动作**: 中心区域物理双击成功。
- **按键序列**: `Up`, `Down`, `Left`, `Right` 依次下发，每键持有 0.15s。

---
*Agentic Workflow V5 修复版现已全面上线并验证通过。*
