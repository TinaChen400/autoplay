import json
import os

class ViewportManager:
    """
    [V6.0] 核心视口管理模块。
    负责 1440x900 逻辑空间与 屏幕物理空间 之间的无缝映射。
    """
    def __init__(self, config_path="config/viewport_config.json"):
        self.config_path = config_path
        self.dock_rect = None  # [V7.38] 新增：用于存储已锁定的窗口物理区域 (x, y, width, height)
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "base_resolution": [1440, 900],
                "user_scale": 1.5, # 默认设为 4K 验证成功的 1.5
                "snap_position": [10, 10],
                "window_keyword": "Tina",
                "offset_x": 12,    # 黄金补偿 X
                "offset_y": 10     # 黄金补偿 Y
            }
        
        self.base_w, self.base_h = self.config["base_resolution"]
        self.user_scale = self.config.get("user_scale", 1.5)
        self.snap_x, self.snap_y = self.config["snap_position"]
        self.ox = self.config.get("offset_x", 12)
        self.oy = self.config.get("offset_y", 10)

    def get_actual_ratio(self, overlay_width):
        """
        [V6.6] 根据当前 Overlay 窗口的逻辑宽度，动态计算真实的物理/逻辑比率。
        用于彻底解决系统 DPI 感知失败导致的对位偏移。
        """
        phys_w, _ = self.get_physical_dims()
        if overlay_width > 0:
            return phys_w / overlay_width
        return self.user_scale

    def project_ai_to_logical(self, ai_x, ai_y, window_rect, relative=False, ratio=None):
        """
        [V6.6] 将 AI 0-1000 坐标投影到逻辑绘图空间。
        """
        scale = ratio if ratio is not None else self.user_scale
        
        # 1. 还原物理偏移量
        ix_phys = (ai_x / 1000.0) * window_rect['width']
        iy_phys = (ai_y / 1000.0) * window_rect['height']
        
        # 2. 映射逻辑坐标
        if relative:
            lx = ix_phys / scale + self.ox
            ly = iy_phys / scale + self.oy
        else:
            lx = (window_rect['left'] + ix_phys) / scale + self.ox
            ly = (window_rect['top'] + iy_phys) / scale + self.oy
        
        return int(lx), int(ly)

    def get_physical_dims(self):
        """计算最终在屏幕上占据的物理像素大小"""
        w = int(self.base_w * self.user_scale)
        h = int(self.base_h * self.user_scale)
        return w, h

    def get_logical_geometry(self, dpi_scale):
        """
        计算 PyQt 绘图需要的逻辑参数（用于抵消系统 DPI 缩放）。
        返回: (x, y, w, h)
        """
        phys_w, phys_h = self.get_physical_dims()
        
        return (
            int(self.snap_x / dpi_scale),
            int(self.snap_y / dpi_scale),
            int(phys_w / dpi_scale),
            int(phys_h / dpi_scale)
        )

    def map_to_physical(self, logic_x, logic_y):
        """
        将 1440x900 的逻辑坐标映射到屏幕上的真实物理坐标。
        """
        # 公式: 物理起始点 + (逻辑坐标 * 用户缩放)
        real_x = self.snap_x + (logic_x * self.user_scale)
        real_y = self.snap_y + (logic_y * self.user_scale)
        return int(real_x), int(real_y)

    def map_to_logical(self, phys_x, phys_y):
        """
        [反向映射] 将屏幕物理点击坐标转回 1440x900 空间。
        """
        logic_x = (phys_x - self.snap_x) / self.user_scale
        logic_y = (phys_y - self.snap_y) / self.user_scale
        return int(logic_x), int(logic_y)

    def update_dock_rect(self, rect_dict):
        """[V7.38] 更新当前锁定的窗口区域信息，供原子技能共享使用"""
        self.dock_rect = rect_dict
