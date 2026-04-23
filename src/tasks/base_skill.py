# -*- coding: utf-8 -*-
"""
BaseSkill: Abstract base class for all atomic skills.
"""

import logging
from abc import ABC, abstractmethod
from src.utils.viewport_manager import ViewportManager
from src.execution.remote_agent import RemoteAgent

# Set up logging
logger = logging.getLogger("BaseSkill")
logger.setLevel(logging.INFO)

class BaseSkill(ABC):
    """
    All skills should inherit from this class to ensure consistency
    in logging, error handling, and environment access.
    """
    
    def __init__(self, viewport_manager: ViewportManager, agent: RemoteAgent = None):
        self.vm = viewport_manager
        # If agent is not provided, create a default one
        self.agent = agent or RemoteAgent()
        
    @abstractmethod
    def execute(self, **kwargs) -> bool:
        """The main logic for the skill."""
        pass

    def log_action(self, message: str):
        logger.info(f"[{self.__class__.__name__}] {message}")

    def log_error(self, message: str):
        logger.error(f"[{self.__class__.__name__}] {message}")
