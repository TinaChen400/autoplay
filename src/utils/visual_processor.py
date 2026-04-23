import cv2
import numpy as np
import os

class VisualProcessor:
    """
    V28 图像处理引擎
    负责生成 A/B 叠合对比图及其他视觉增强处理。
    """
    def __init__(self, records_dir=r"D:\Dev\autoplay\records"):
        self.records_dir = records_dir

    def create_comparison_overlay(self, img_a_path, img_b_path, output_name="snap_overlay.jpg"):
        """
        生成 A 和 B 的半透明叠合图。
        A 显红色调，B 显绿色调，重合部分显正常色或混合色。
        """
        try:
            img_a = cv2.imread(img_a_path)
            img_b = cv2.imread(img_b_path)

            if img_a is None or img_b is None:
                print(f"[VISUAL] 错误: 无法读取图片 {img_a_path} 或 {img_b_path}")
                return None

            # 确保尺寸一致
            if img_a.shape != img_b.shape:
                img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))

            # 方案：加权融合
            # alpha 为 img_a 的权重，1-alpha 为 img_b 的权重
            overlay = cv2.addWeighted(img_a, 0.5, img_b, 0.5, 0)
            
            # 增强对比：计算差异并叠加
            diff = cv2.absdiff(img_a, img_b)
            # 将差异图转为伪彩色以便识别
            diff_color = cv2.applyColorMap(diff, cv2.COLORMAP_JET)
            
            # 最终结果：50% 混合图 + 50% 差异热力图
            final_result = cv2.addWeighted(overlay, 0.7, diff_color, 0.3, 0)

            output_path = os.path.join(self.records_dir, output_name)
            cv2.imwrite(output_path, final_result)
            print(f"[VISUAL] 叠合对比图已生成: {output_path}")
            return output_path
        except Exception as e:
            print(f"[VISUAL] 叠合图生成失败: {e}")
            return None

    def create_side_by_side(self, img_list, output_name="snap_combined.jpg"):
        """将多张图水平拼接"""
        try:
            imgs = [cv2.imread(p) for p in img_list if os.path.exists(p)]
            if not imgs: return None
            
            # 统一高度
            min_h = min(i.shape[0] for i in imgs)
            resized = [cv2.resize(i, (int(i.shape[1] * min_h / i.shape[0]), min_h)) for i in imgs]
            
            combined = np.hstack(resized)
            output_path = os.path.join(self.records_dir, output_name)
            cv2.imwrite(output_path, combined)
            return output_path
        except:
            return None
