import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'essays.db')

os.makedirs(DATA_DIR, exist_ok=True)

TARGET_WEBSITES = [
    {
        'id': 1,
        'name': '网站1',
        'url': '',
        'list_selector': '',
        'title_selector': '',
        'content_selector': '',
        'enabled': True
    },
    {
        'id': 2,
        'name': '网站2',
        'url': '',
        'list_selector': '',
        'title_selector': '',
        'content_selector': '',
        'enabled': True
    },
    {
        'id': 3,
        'name': '网站3',
        'url': '',
        'list_selector': '',
        'title_selector': '',
        'content_selector': '',
        'enabled': True
    },
    {
        'id': 4,
        'name': '网站4',
        'url': '',
        'list_selector': '',
        'title_selector': '',
        'content_selector': '',
        'enabled': True
    },
    {
        'id': 5,
        'name': '网站5',
        'url': '',
        'list_selector': '',
        'title_selector': '',
        'content_selector': '',
        'enabled': True
    }
]

DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/'
}

REQUEST_DELAY = 1

MAX_RETRY = 3

LOG_LEVEL = 'INFO'

LOG_FILE = os.path.join(DATA_DIR, 'app.log')
