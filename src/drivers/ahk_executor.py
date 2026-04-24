import subprocess
import os

class AHKExecutor:
    """
    操作执行模块，基于 AutoHotkey 实现底层点击、输入与页面清空。
    """
    def __init__(self, ahk_path: str, logger=None):
        self.ahk_path = ahk_path
        self.logger = logger

    def log_error(self, msg):
        if self.logger:
            self.logger.log("ERROR", msg)
        else:
            print(f"[ERROR] {msg}")

    def execute_click(self, x: int, y: int):
        """执行全屏绝对坐标点击"""
        script = f"CoordMode, Mouse, Screen\nSetDefaultMouseSpeed, 0\nClick, {x}, {y}\nSoundBeep, 750, 200"
        self._run_script(script)

    def execute_input(self, text: str):
        """执行文本输入"""
        script = f"Send, {text}\nSoundBeep, 1000, 200"
        self._run_script(script)

    def execute_shortcut(self, keys: str):
        """执行快捷键命令（如 ^r, {F5} 等）"""
        script = f"Send, {keys}\nSoundBeep, 500, 300"
        self._run_script(script)

    def clear_page(self):
        """
        触发远程页面清空操作。
        模拟组合键，如 Ctrl+A -> Backspace 或 刷新。
        """
        # 示例脚本：清空远程桌面痕迹
        script = "Send, ^a\nSleep, 100\nSend, {Backspace}"
        self._run_script(script)
        return True

    def _run_script(self, script_content: str):
        """运行临时 AHK 脚本"""
        temp_file = "temp_exec.ahk"
        try:
            with open(temp_file, "w", encoding="utf-8-sig") as f:
                f.write(script_content)
            
            # 使用 subprocess 调用 AHK
            if os.path.exists(self.ahk_path):
                subprocess.run([self.ahk_path, temp_file], check=True)
            else:
                err_msg = f"未找到 AHK 程序 at {self.ahk_path}，物理物理模拟已失效！"
                self.log_error(err_msg)
        except Exception as e:
            self.log_error(f"AHK 执行异常: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
