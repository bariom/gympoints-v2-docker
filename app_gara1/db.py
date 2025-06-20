import sqlite3

def get_connection():
    return sqlite3.connect("gym.db", check_same_thread=False)
