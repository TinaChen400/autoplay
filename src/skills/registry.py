# -*- coding: utf-8 -*-
"""
SkillRegistry: Maps skill names to actual Python execution functions.
"""

import logging
from typing import Callable, Dict, Any, Optional

# Set up logging
logger = logging.getLogger("SkillRegistry")
logger.setLevel(logging.INFO)

class SkillRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
            cls._instance.handlers = {}
        return cls._instance

    def register(self, skill_type: str, handler: Callable):
        """Registers a function handler for a skill type."""
        self.handlers[skill_type] = handler
        logger.info(f"Registered handler for skill type: {skill_type}")

    def get_handler(self, skill_type: str) -> Optional[Callable]:
        """Retrieves the handler for a skill type."""
        return self.handlers.get(skill_type)

# Singleton helper
registry = SkillRegistry()

def skill_handler(skill_type: str):
    """Decorator to register a skill handler."""
    def decorator(func):
        registry.register(skill_type, func)
        return func
    return decorator
