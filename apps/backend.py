"""
Backend module for offering various functions.
"""

import random

def generate():
    """Generates a random number from 0 to 99

    Returns:
        int: Generated number.
    """
    return random.randrange(0, 100)
