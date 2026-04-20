# 🚥 远程智控工位：每日启动指南 (V5)

欢迎回来！按照以下步骤即可瞬间恢复自动化环境。

## 1. 基础环境唤醒
打开 PowerShell 终端并导航至项目根目录：
```powershell
cd D:\Dev\autoplay
.\.venv\Scripts\activate
```

## 2. 启动指挥中心 (HUD)
运行增强型物理对位相框：
```powershell
python src\ui\visual_dock_v2.py
```
- **核心操作快捷键**:
  - `Tab`: 在已连接的远程主机（MSI / Oliver）间一键切换。
  - `F5`: **[全自动校准]** 强制更新当前主机的物理像素位置。
  - `F6`: **[所见即所得截图]** 抓取当前相框内的 1:1 物理画面。
  - `Esc`: 安全退出所有监控进程。

## 3. 执行已录制技能
若需运行自动化交互（如识别并点击小图）：
```powershell
python src\tasks\msi_skills.py
```

## 4. 注意事项
- **DPI 缩放**: 请保持显示器缩放比例不变（目前已知您的环境为 150%）。
- **档案同步**: 坐标数据始终保存在 `config/profiles.json`，已推送到 GitHub。
- **存证查看**: 所有的操作截图都会自动记录在 `records/` 目录下。

---
*祝今日任务执行圆满成功！Agentic Workflow is Ready.*
