import sqlite3
import os
from datetime import datetime
from config import DB_PATH


class CacheManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._init_db()

    def _init_db(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_name TEXT NOT NULL,
                category TEXT,
                grade TEXT,
                word_count INTEGER,
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                unique_key TEXT UNIQUE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawl_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def insert_essay(self, essay):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO essays 
                (title, content, source_url, source_name, category, grade, word_count, unique_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                essay['title'],
                essay['content'],
                essay['source_url'],
                essay['source_name'],
                essay.get('category', ''),
                essay.get('grade', ''),
                essay.get('word_count', 0),
                essay['unique_key']
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        except Exception as e:
            return None

    def get_all_essays(self):
        self.cursor.execute('SELECT * FROM essays ORDER BY crawl_time DESC')
        return self.cursor.fetchall()

    def get_essay_by_id(self, essay_id):
        self.cursor.execute('SELECT * FROM essays WHERE id = ?', (essay_id,))
        return self.cursor.fetchone()

    def search_essays(self, keyword=None, source=None, category=None):
        query = 'SELECT * FROM essays WHERE 1=1'
        params = []
        
        if keyword:
            query += ' AND (title LIKE ? OR content LIKE ?)'
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        if source:
            query += ' AND source_name = ?'
            params.append(source)
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        query += ' ORDER BY crawl_time DESC'
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def insert_log(self, source_name, url, status, message=''):
        self.cursor.execute('''
            INSERT INTO crawl_logs (source_name, url, status, message)
            VALUES (?, ?, ?, ?)
        ''', (source_name, url, status, message))
        self.conn.commit()

    def get_logs(self, limit=100):
        self.cursor.execute('SELECT * FROM crawl_logs ORDER BY crawl_time DESC LIMIT ?', (limit,))
        return self.cursor.fetchall()

    def get_stats(self):
        self.cursor.execute('SELECT COUNT(*) FROM essays')
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT source_name, COUNT(*) FROM essays GROUP BY source_name')
        by_source = dict(self.cursor.fetchall())
        
        return {'total': total, 'by_source': by_source}

    def close(self):
        if self.conn:
            self.conn.close()
