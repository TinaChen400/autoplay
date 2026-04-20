# Task List V4 - 智能视觉对位与按键交互

- [x] **Step 1: 基础设施增强**
    - [x] 在 `RemoteAgent` 中封装硬件级按键序列执行器。
- [x] **Step 2: 核心算法实现**
    - [x] 在 `MSISkills` 中实现 `wait_for_visual_change` 方法（基于 `cv2.absdiff`）。
- [x] **Step 3: 业务技能封装**
    - [x] 实现 `interact_with_large_image` 方法，集成视觉等待与方向键操作。
- [x] **Step 4: 冒烟测试与验证**
    - [x] 验证在加载过程中的“智能等待”逻辑。
    - [x] 确认退出后大图保持打开状态。
