# Walkthrough V13: 像素归一化与视觉终极咬合

本版本通过动态比例探测与原子化坐标对位，彻底解决了高 DPI 环境下的 HUD 失准问题。

## 技术里程碑

1.  **动态 Ratio 适配 (Dynamic Scaling)**：
    - 抛弃硬编码比例，实时调用 `screen().devicePixelRatio()`。
    - 完美支持 100%, 125%, 150%, 200% 等各种 Windows 缩放环境。
2.  **原子化对位 (Atomic Alignment)**：
    - 拆分 `move()` 与 `setFixedSize()`。
    - 解决了 `setGeometry` 在复杂缩放环境下的单位计算冲突。
3.  **全能实时跟随**：
    - 3.3 FPS 的高频同步，确保窗口移动时 UI 0 掉队。

## 使用指引

- **验证跟随**: 移动 Chrome 窗口，观察绿框是否紧贴。
- **点击测试**: 点击卡片 1。此时后台已集成线程安全版 MSS，将精准点开缩略图。

---
*Agentic Workflow V13 终极对位版已正式交付。*
