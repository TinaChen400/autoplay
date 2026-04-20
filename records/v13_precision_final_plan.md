# Implementation Plan V13: 像素归一化与对位终极修复

本计划旨在通过动态探测 Qt 的真实缩放比例，彻底解决 V12 中出现的“蓝框巨显”与吸附失效问题。

## 修复策略

1.  **动态 Ratio 适配**：
    *   移除硬编码的 `1.5`。
    *   直接使用 `self.screen().devicePixelRatio()` 获取 Qt 眼中的缩放比例。
    *   **坐标归位**：使用 `self.move()` 和 `self.setFixedSize()` 分离物理对位，优先使用逻辑像素进行 UI 绘制。
2.  **颜色对位统一**：
    *   吸附状态 (is_docked) 一律显示 **高亮绿**，解除用户对颜色的困惑。
3.  **万能持锁优化**：
    *   增强 `Space-to-Lock` 的视觉反馈。当识别成功时，面板底部会闪烁提示。
4.  **大脑稳定性保障**：
    *   集成已修复的 `MSISkills`（线程安全截图），确保卡片点击不再报 `_thread._local` 错误。

## 变更内容

### 1. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 改用动态 `devicePixelRatio` 进行缩放计算。
- 修正 `setGeometry` 的宽度累加错误。

## 验证计划

1. **零偏差对位**：重启后绿框必须贴合 Chrome 窗口（非 0,0 坐标偏移）。
2. **逻辑一致性**：点击卡片 1，观察控制台是否成功输出 Hardware-clicking 且不再报错。
