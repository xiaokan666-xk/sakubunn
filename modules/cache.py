import sqlite3
import os
import hashlib
from datetime import datetime, timedelta
from config import DB_PATH


class CacheManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                school TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL DEFAULT '',
                site TEXT NOT NULL DEFAULT '',
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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_updates (
                site_name TEXT PRIMARY KEY,
                site_url TEXT NOT NULL,
                last_crawl_time DATETIME,
                last_essay_count INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def _generate_unique_key(self, essay):
        raw = f"{essay.get('title', '')}{essay.get('author', '')}{essay.get('source', '')}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def insert_essay(self, essay):
        try:
            unique_key = self._generate_unique_key(essay)
            self.cursor.execute('''
                INSERT OR IGNORE INTO essays 
                (title, author, school, body, source, date, site, unique_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                essay.get('title', ''),
                essay.get('author', ''),
                essay.get('school', ''),
                essay.get('body', ''),
                essay.get('source', ''),
                essay.get('date', ''),
                essay.get('site', ''),
                unique_key
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        except Exception as e:
            print(f"Insert essay error: {e}")
            return None

    def get_all_essays(self):
        self.cursor.execute('SELECT * FROM essays ORDER BY crawl_time DESC')
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_essay_by_id(self, essay_id):
        self.cursor.execute('SELECT * FROM essays WHERE id = ?', (essay_id,))
        row = self.cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def search_essays(self, keyword=None, source=None, date_from=None, date_to=None):
        query = 'SELECT * FROM essays WHERE 1=1'
        params = []

        if keyword:
            query += ' AND (title LIKE ? OR author LIKE ? OR body LIKE ?)'
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

        if source:
            query += ' AND site = ?'
            params.append(source)

        if date_from:
            query += ' AND crawl_time >= ?'
            params.append(date_from)

        if date_to:
            query += ' AND crawl_time <= ?'
            params.append(date_to)

        query += ' ORDER BY crawl_time DESC'
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_essays_by_ids(self, ids):
        if not ids:
            return []
        placeholders = ','.join('?' * len(ids))
        self.cursor.execute(f'SELECT * FROM essays WHERE id IN ({placeholders})', ids)
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_essays_by_date_range(self, date_from=None, date_to=None):
        return self.search_essays(date_from=date_from, date_to=date_to)

    def get_essays_by_relative_time(self, days=None, months=None):
        now = datetime.now()
        if months:
            date_from = (now - timedelta(days=months * 30)).strftime('%Y-%m-%d %H:%M:%S')
        elif days:
            date_from = (now - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            return self.get_all_essays()
        return self.search_essays(date_from=date_from)

    def get_site_last_update(self, site_name):
        self.cursor.execute('''
            SELECT MAX(crawl_time) FROM essays WHERE site = ?
        ''', (site_name,))
        result = self.cursor.fetchone()
        return result[0] if result and result[0] else None

    def get_all_site_updates(self):
        self.cursor.execute('''
            SELECT site, MAX(crawl_time), COUNT(*) FROM essays GROUP BY site
        ''')
        rows = self.cursor.fetchall()
        result = {}
        for row in rows:
            result[row[0]] = {
                'last_update': row[1],
                'essay_count': row[2]
            }
        return result

    def update_site_crawl_time(self, site_name, site_url):
        self.cursor.execute('''
            INSERT OR REPLACE INTO site_updates (site_name, site_url, last_crawl_time)
            VALUES (?, ?, ?)
        ''', (site_name, site_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()

    def get_site_crawl_info(self):
        self.cursor.execute('SELECT * FROM site_updates')
        rows = self.cursor.fetchall()
        result = {}
        for row in rows:
            result[row[0]] = {
                'site_url': row[1],
                'last_crawl_time': row[2],
                'last_essay_count': row[3]
            }
        return result

    def essay_exists(self, source_url):
        self.cursor.execute('SELECT id FROM essays WHERE source = ? LIMIT 1', (source_url,))
        return self.cursor.fetchone() is not None

    def _row_to_dict(self, row):
        return {
            'id': row[0],
            'title': row[1],
            'author': row[2],
            'school': row[3],
            'body': row[4],
            'source': row[5],
            'date': row[6],
            'site': row[7],
            'crawl_time': row[8],
            'unique_key': row[9]
        }

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

        self.cursor.execute('SELECT site, COUNT(*) FROM essays GROUP BY site')
        by_source = dict(self.cursor.fetchall())

        return {'total': total, 'by_source': by_source}

    def close(self):
        if self.conn:
            self.conn.close()
