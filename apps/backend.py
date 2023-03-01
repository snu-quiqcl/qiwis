"""
Backend module for offering various functions.
"""

import random
import sqlite3

def generate() -> int:
    """Generates a random number from 0 to 99.

    Returns:
        Generated number.
    """
    return random.randrange(0, 100)


def read(db_path: str, table: str):
    """Reads the value from the database.

    It can only read the last row in a specific table.

    Database structure:
        There is at least one table and in the table, there is at least one column.
        The value to read should be in the first column.

    Error handling:
        An error may occur if it tries to access the database before another one commits.
        If so, the error will be catched by try-except statement and showed.
        See the returning value in returns description. 

    Args:
        db_path: A path of database file.
          It will be "None" if the user does not select a specific database. 
        table: A name of table to read.

    Returns:
        The read value if reading is successful, otherwise None.
    """
    if db_path == "None":
        return None
    con = sqlite3.connect(db_path)
    try:
        with con:
            value = con.execute(
                f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1"
            ).fetchone()[0]
    except sqlite3.Error as e:
        print(f"apps.backend.read(): {e!r}")
        return None
    finally:
        con.close()
    return value


def write(db_path: str, table: str, value) -> bool:
    """Writes the value to the database.

    It can only add the value into the last row in a specific table.
    The value and saved time are read in the first and second column, respectively. 

    Database structure:
        See read().

    Error handling:
        An error may occur if it tries to access the database before another one commits.
        If so, the error will be catched by try-except statement and showed.
        See the returning value in returns description. 

    Args:
        db_path: A path of database file.
          It will be None if the user does not select a specific database.
        table: A name of table to write down.
        value: A value to write to the given location.

    Returns:
        True if writing is successful, otherwise False.
    """
    if db_path == "None":
        return False
    con = sqlite3.connect(db_path)
    try:
        with con:
            con.execute(
                f"INSERT INTO {table} VALUES (?, datetime('now', 'localtime'))", 
                (value,)
            )
    except sqlite3.Error as e:
        print(f"apps.backend.write(): {e!r}")
        return False
    finally:
        con.close()
    return True
