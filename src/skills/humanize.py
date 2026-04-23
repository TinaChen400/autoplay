# -*- coding: utf-8 -*-
"""
Humanize: Adds randomized delays and jitter to simulate human interaction.
"""

import time
import random
import logging
from typing import Tuple

# Set up logging
logger = logging.getLogger("Humanize")
logger.setLevel(logging.INFO)

def random_delay(min_sec: float = 0.5, max_sec: float = 2.0):
    """Sleeps for a random duration between min and max."""
    duration = random.uniform(min_sec, max_sec)
    time.sleep(duration)

def jitter_pos(x: int, y: int, offset_range: int = 5) -> Tuple[int, int]:
    """Adds a small random offset to a coordinate."""
    dx = random.randint(-offset_range, offset_range)
    dy = random.randint(-offset_range, offset_range)
    return (x + dx, y + dy)

def simulate_think_time(min_sec: float = 1.0, max_sec: float = 3.0):
    """Simulates 'thinking' pause between actions."""
    logger.debug("Simulating think time...")
    random_delay(min_sec, max_sec)
