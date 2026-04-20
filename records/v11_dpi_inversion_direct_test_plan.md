# Implementation Plan V11: DPI 逆向补偿与 Agent 效能直接测试

本计划旨在通过反向计算消除 Qt 的二次缩放干扰，实现指挥中心的物理级重合，并直接验证 Agent 的点击精准度。

## 修复策略

1.  **DPI 逆向补偿 (Inversion Logic)**：
    *   在 `VisualDockV2` 中引入全局缩放因子 `self.scale = 1.5`。
    *   所有从 DWM 获取的物理坐标，在交给 Qt `setGeometry` 前全部 **除以 1.5**。
2.  **直接点击测试 (Direct Execution)**：
    *   按照用户要求，不再仅仅展示边框，而是直接驱动 Agent 尝试点击缩略图中心。
    *   我们将运行一个“盲测”脚本，绕过 HUD 干扰，直接从屏幕底层进行视觉对位并触发硬件点击。

## 变更内容

### 1. [Visual Dock UI](file:///d:/Dev/autoplay/src/ui/visual_dock_v2.py) [MODIFY]
- 适配 `to_logical()` 转换函数，确保渲染对位。

### 2. [Automated Test Script] [NEW]
- 创建 `scratch/direct_vision_test.py`：仅使用视觉对位逻辑（V7 版），直接在 150% 环境下尝试点击 `SOURCE` 下方的图片。

## 验证计划

1. **视觉完美重合**：启动 V11 后，确认绿框不再“变大”，而是精准覆盖 Chrome 窗口。
2. **硬件点击验证**：运行直接测试脚本，确认浏览器中的缩略图被成功点开。
