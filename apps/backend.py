"""
Backend module for offering various functions.
"""

import random
import sqlite3
from datetime import datetime

def generate() -> int:
    """Generates a random number from 0 to 99.

    Returns:
        Generated number.
    """
    return random.randrange(0, 100)


def read(db_path: str, table: str):
    """Reads the value from the database.

    Args:
        db_path: A path of database file.
        table: A name of table to read.

    Returns:
        The read value if reading is successful, otherwise None.
    """
    if db_path == "None":  # if there is no database
        return None
    con = sqlite3.connect(db_path)
    try:
        with con:
            value = con.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    except sqlite3.Error as e:
        print(e)
        return None
    con.close()
    return value


def write(db_path: str, table: str, value) -> bool:
    """Writes the value to the database.

    Args:
        db_path: A path of database file.
        table: A name of table to write down.
        value: A value to write to the given location.

    Returns:
        True if writing is successful, otherwise False.
    """
    if db_path == "None":  # if there is no database
        return False
    con = sqlite3.connect(db_path)
    try:
        with con:
            con.execute(f"INSERT INTO {table} VALUES (?, ?)", (value, str(datetime.now())))
    except sqlite3.Error as e:
        print(e)
        return False
    con.close()
    return True
