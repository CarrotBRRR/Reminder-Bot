"""
DBController.py
===
Controls the database for the Reminder Bot

Authors: 
-----
Dominic Choi
    GitHub: [CarrotBRRR](https://github.com/CarrotBRRR)
"""

import os
import json

class DBController:
    """
    DBController
    ===
    Controls the JSON database 

    Attributes:
    ----------
    db_path : str
        The path to the database file
    db : dict
        The database object

    Methods:
    -------
    __init__(self, db_path: str)
        Initializes the DBController with the given database path
    load_db(self)
        Loads the database from the file
    save_db(self)
        Saves the database to the file

    add_obj(self, reminder: dict)
        Adds an item to the database
    del_obj(self, reminder: dict)
        Deletes an item from the database
    """
    def __init__(self, db_path: str):
        """
        Initializes the DBController with the given database path

        Parameters:
        ----------
        db_path : str
            The path to the database file
        """
        self.db_path = db_path
        self.db = {}

    def load_db(self):
        """
        Loads the database from the file
        """
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as db_file:
                self.db = json.load(db_file)
        else:
            self.db = {}