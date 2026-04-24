# -*- coding: utf-8 -*-
"""
SkillExecutor: Orchestrates the execution of skills and panels.
"""

import logging
from typing import Dict, List, Any, Optional
from src.skills.loader import SkillLoader
from src.skills.registry import registry
from src.skills.humanize import random_delay, jitter_pos, simulate_think_time
from src.core.viewport import ViewportManager

# Set up logging
logger = logging.getLogger("SkillExecutor")
logger.setLevel(logging.INFO)

class SkillExecutor:
    def __init__(self, viewport_manager: ViewportManager):
        self.vm = viewport_manager
        self.loader = SkillLoader()
        
    def execute_skill(self, skill_id: str, override_params: Dict = None) -> bool:
        """
        Executes a single skill by its ID.
        """
        skill_def = self.loader.get_skill_def(skill_id)
        if not skill_def:
            logger.error(f"Skill definition not found: {skill_id}")
            return False
            
        # Merge default params with overrides
        params = skill_def.get("params", {}).copy()
        if override_params:
            params.update(override_params)
            
        category = skill_def.get("category", "generic")
        handler = registry.get_handler(skill_id) or registry.get_handler(category)
        
        if not handler:
            logger.error(f"No handler registered for skill: {skill_id} or category: {category}")
            return False
            
        try:
            logger.info(f"Executing Skill: {skill_id} ({skill_def.get('description', '')})")
            # All skills are expected to handle coordinate mapping if they take x, y
            return handler(self.vm, **params)
        except Exception as e:
            logger.error(f"Error executing skill {skill_id}: {e}")
            return False

    def execute_panel(self, panel_config: Dict) -> bool:
        """
        Executes a sequence of skills defined in a panel configuration.
        """
        panel_name = panel_config.get("name", "Unknown Panel")
        steps = panel_config.get("steps", [])
        
        logger.info(f"--- Starting Panel: {panel_name} ({len(steps)} steps) ---")
        
        for step in steps:
            step_name = step.get("name", f"Step {step.get('id')}")
            skill_id = step.get("skill")
            params = step.get("params", {})
            
            logger.info(f"Step: {step_name}")
            success = self.execute_skill(skill_id, params)
            
            if not success:
                logger.error(f"Step '{step_name}' failed. Aborting panel.")
                return False
                
            # Optional: Humanization delay between steps
            random_delay(0.5, 1.5)
            
        logger.info(f"--- Panel '{panel_name}' completed successfully ---")
        return True
