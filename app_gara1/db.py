import sqlite3

def get_connection():
    return sqlite3.connect("gym2.db", check_same_thread=False)
