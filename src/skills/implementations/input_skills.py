import time
import random
import pydirectinput
import win32api
import win32con

class InputSkillsMixin:
    def press_keys(self, keys, interval=0.5):
        """物理注入按键流"""
        self._log(f"Executing press_keys: {keys} with interval {interval}")
        for key in keys:
            pydirectinput.press(key)
            time.sleep(interval if isinstance(interval, (int, float)) else self._parse_range(interval))
        return True

    def human_scroll(self, distance=400, steps=5):
        """拟人化碎步滚动"""
        self._log(f"Executing human_scroll: distance={distance}, steps={steps}")
        for i in range(steps):
            amount = - (distance // steps)
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
            time.sleep(random.uniform(0.1, 0.3))
        return True

    def sleep(self, seconds=1.0):
        """随机延时"""
        duration = self._parse_range(seconds) if isinstance(seconds, str) else seconds
        self._log(f"Executing sleep: {duration}s")
        time.sleep(duration)
        return True

    def action_press_keys(self, keys, interval=0.5):
        return self.press_keys(keys, interval)

    def action_sleep(self, seconds=1.0):
        return self.sleep(seconds)

    def action_scroll_home_end(self, direction="end"):
        self._log(f"Executing action_scroll_home_end: {direction}")
        key = "end" if direction == "end" else "home"
        pydirectinput.press(key)
        return True

    def _parse_range(self, range_str):
        if "-" in range_str:
            parts = range_str.split("-")
            return random.uniform(float(parts[0]), float(parts[1]))
        return float(range_str)
