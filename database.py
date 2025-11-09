import sqlite3
import threading

class Database:
    def __init__(self, db_name='healthcare_chatbot.db'):
        self.db_name = db_name
        self.thread_local = threading.local()

    def get_connection(self):
        if not hasattr(self.thread_local, "connection"):
            self.thread_local.connection = sqlite3.connect(self.db_name)
        return self.thread_local.connection

    def get_cursor(self):
        return self.get_connection().cursor()

    def create_tables(self):
        cursor = self.get_cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            user_name TEXT,
            symptom TEXT,
            days INTEGER,
            additional_symptoms TEXT,
            diagnosis TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.get_connection().commit()

    def save_conversation(self, user_name, symptom, days, additional_symptoms, diagnosis):
        cursor = self.get_cursor()
        cursor.execute('''
        INSERT INTO conversations (user_name, symptom, days, additional_symptoms, diagnosis)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_name, symptom, days, ','.join(additional_symptoms), diagnosis))
        self.get_connection().commit()

    def get_user_history(self, user_name):
        cursor = self.get_cursor()
        cursor.execute('SELECT * FROM conversations WHERE user_name = ?', (user_name,))
        return cursor.fetchall()

    def close(self):
        if hasattr(self.thread_local, "connection"):
            self.thread_local.connection.close()
            del self.thread_local.connection