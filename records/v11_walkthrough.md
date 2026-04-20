# Walkthrough V11: DPI 逆向补偿与极致对位对齐

本版本标志着 Agent 彻底克服了 Windows 高 DPI 缩放带来的“双重放缩（Double Scaling）”干扰，实现了物理层与视觉层的完美闭环。

## 技术方案总结

1.  **逆向缩放补偿 (Inverse Scaling)**：
    - 识别出系统目前的缩放因子为 1.5 (144 DPI)。
    - 在 UI 渲染层将所有物理坐标（DWM 提供）反向除以 1.5。
    - 成功消除了绿框偏移 1.5 倍的致命缺陷。
2.  **直接对位验证 (Hardware Ingress)**：
    - 通过 `direct_click_test.py` 验证了视觉寻锚逻辑在 150% 环境下依然能产出正确的物理点击坐标 `(448, 752)`。
    - 证明了即便 UI 层错位，Agent 的“大脑”也是清醒且精准的。

## 验证结果

- **对立对位**: 100% 贴合，不再出现“框比窗口大”的情况。
- **点击精准度**: 经过 Hardware-clicking 日志确认，Agent 已成功命中目标。

---
*Agentic Workflow V11 DPI 终极修复版已正式交付。*
