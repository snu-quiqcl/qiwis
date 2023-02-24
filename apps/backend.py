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


def save(_num: int, db_name: str):
    """Store the number in the database.

    Args:
        num: Number to store
        db_name: A string that indicates the name of database

    Returns:
        bool: True if store succeeds, otherwise False.
    """
    if db_name == "None":
        return False

    return True
