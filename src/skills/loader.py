# -*- coding: utf-8 -*-
"""
SkillLoader: Loads skill definitions from JSON configurations.
"""

import os
import json
import logging
from typing import Dict, List, Optional

# Set up logging
logger = logging.getLogger("SkillLoader")
logger.setLevel(logging.INFO)

class SkillLoader:
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            self.skills_dir = os.path.join(os.getcwd(), 'config', 'skills')
        else:
            self.skills_dir = skills_dir
            
        self.skills = {}
        self.load_all_skills()

    def load_all_skills(self) -> None:
        """Loads all .json files from the skills directory."""
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.skills_dir, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Add skills to the master dictionary
                        self.skills.update(data)
                    logger.info(f"Loaded skills from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load skills from {filename}: {e}")

    def get_skill_def(self, skill_id: str) -> Optional[Dict]:
        """Returns the definition of a specific skill."""
        return self.skills.get(skill_id)

    def list_skills(self) -> List[str]:
        """Returns a list of all available skill IDs."""
        return list(self.skills.keys())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = SkillLoader()
    print(f"Available Skills: {loader.list_skills()}")
