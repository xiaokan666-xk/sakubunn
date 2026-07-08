import requests
import time
import logging
from config import DEFAULT_REQUEST_HEADERS, REQUEST_DELAY, MAX_RETRY


class Crawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_REQUEST_HEADERS)
        self.logger = logging.getLogger(__name__)

    def fetch(self, url, timeout=30, retry=True):
        attempts = 0
        while attempts < (MAX_RETRY if retry else 1):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                self.logger.info(f'Fetched: {url}')
                time.sleep(REQUEST_DELAY)
                return response.text
            except requests.exceptions.RequestException as e:
                attempts += 1
                self.logger.warning(f'Fetch failed (attempt {attempts}/{MAX_RETRY}): {url} - {str(e)}')
                if attempts < MAX_RETRY:
                    time.sleep(2)
        
        self.logger.error(f'Failed to fetch: {url}')
        return None

    def fetch_binary(self, url, timeout=30):
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            self.logger.error(f'Failed to fetch binary: {url} - {str(e)}')
            return None

    def download_file(self, url, save_path):
        content = self.fetch_binary(url)
        if content:
            with open(save_path, 'wb') as f:
                f.write(content)
            return True
        return False
