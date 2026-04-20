# Implementation Plan V7: 自适应视觉矩形对位 (Integrated ROI Targeting)

本计划旨在将验证成功的 OpenCV 轮廓探测逻辑集成到 `MSISkills` 中，通过“视觉扫描”替代“静态坐标”，彻底解决图片位置/大小变化导致的点击失效问题。

## 变更内容

### 1. [MSI Skills](file:///d:/Dev/autoplay/src/tasks/msi_skills.py)
- **新增 `find_thumbnail_rect(anchor_at)`**：
    - 输入：地标文字的中点坐标。
    - 逻辑：基于地标坐标划定 300x300 的局部搜索区域 (ROI)。
    - 算法：使用 `cv2.findContours` 提取区域内所有非背景矩形，并根据面积和长宽比（50-150px）寻找最匹配的缩略图框。
    - 返回：检测到的图片中心点物理坐标。
- **重构 `click_input_thumbnail()`**：
    - 将原本的 `target_abs_y = base_y + anchor_y + 120` 硬编码逻辑改为调用 `find_thumbnail_rect`。

## 核心算法优势

*   **100% 容错**：只要图片在文字下方 300 像素范围内，无论它怎么动，Agent 都能“摸”到中心。
*   **物理精度**：完美适配 V6 的 DPI 感知逻辑。

## 验证计划

1. **多重验证**：在页面处于不同滚动位置、不同图片大小时运行脚本。
2. **可视化验证**：运行过程仍会生成包含识别框的快照，供您实时审计识别精度。
