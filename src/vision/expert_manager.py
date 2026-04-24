import yaml
import os

class ExpertManager:
    """
    V28 专家知识库管理器
    负责加载 YAML 经验包并为 LLM 生成动态 Prompt 扩展。
    """
    def __init__(self, config_path=r"D:\Dev\autoplay\config\expert_knowledge.yaml"):
        self.config_path = config_path
        self.knowledge = {}
        self.load_knowledge()

    def load_knowledge(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.knowledge = yaml.safe_load(f) or {}
                print(f"[EXPERT] 知识库加载成功: {len(self.knowledge.get('profiles', {}))} 个专业档案已就绪")
            else:
                self.knowledge = {}
                print(f"[EXPERT] 错误: 未找到知识库文件 {self.config_path}")
        except Exception as e:
            self.knowledge = {}
            print(f"[EXPERT] 知识库加载失败: {e}")

    def get_profile(self, profile_name):
        """获取特定档案的内容"""
        return self.knowledge.get("profiles", {}).get(profile_name)

    def generate_prompt_extension(self, profile_name):
        """将 YAML 经验转换为供 LLM 阅读的指令文本"""
        profile = self.get_profile(profile_name)
        if not profile:
            return ""

        ext = f"\n### 专家评估建议 ({profile.get('name', profile_name)}) ###\n"
        
        # 注入分析准则
        criteria = profile.get("criteria", [])
        if criteria:
            ext += "在分析图片时，请务必参考以下专业标准：\n"
            for item in criteria:
                ext += f"- {item}\n"
        
        # 注入强制规则
        rules = profile.get("rules", {})
        if rules:
            ext += "\n**系统性强制约束**：\n"
            for key, val in rules.items():
                ext += f"- 对于 {key} 维度的打分，请遵循：{val}\n"
        
        return ext

    def match_profile_by_keywords(self, text):
        """根据关键词（比如豆包的预审结果）自动匹配档案名"""
        text = text.lower()
        profiles = self.knowledge.get("profiles", {})
        for name, data in profiles.items():
            keywords = data.get("detect_keywords", [])
            if any(k.lower() in text for k in keywords):
                return name
        return None
