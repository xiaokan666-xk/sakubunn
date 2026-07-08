import re
import logging
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class SpiderBase(ABC):
    site_name = ""
    site_url = ""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def fetch(self, url: str, timeout: int = 30) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except requests.RequestException as e:
            self.logger.error(f'Fetch failed [{self.site_name}] {url}: {e}')
            return None
    
    def fetch_binary(self, url: str, timeout: int = 30) -> Optional[bytes]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            self.logger.error(f'Fetch binary failed [{self.site_name}] {url}: {e}')
            return None
    
    def get_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, 'html.parser')
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ''
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\r\n', '\n', text)
        return text.strip()
    
    def make_essay(self, title='', author='', school='', body='', source='', date='') -> Dict:
        return {
            'title': self.clean_text(title),
            'author': self.clean_text(author),
            'school': self.clean_text(school),
            'body': self.clean_text(body),
            'source': source,
            'date': self.clean_text(date),
            'site': self.site_name
        }
    
    @abstractmethod
    def get_essay_list_urls(self) -> List[str]:
        pass
    
    @abstractmethod
    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        pass
    
    def crawl(self, max_count: int = None) -> List[Dict]:
        essays = []
        list_urls = self.get_essay_list_urls()
        self.logger.info(f'[{self.site_name}] Found {len(list_urls)} list pages')
        
        for list_url in list_urls:
            html = self.fetch(list_url)
            if not html:
                continue
            
            items = self.parse_list_page(html, list_url)
            self.logger.info(f'[{self.site_name}] Found {len(items)} essay links in {list_url}')
            
            for item in items:
                if max_count and len(essays) >= max_count:
                    break
                
                essay_url = item.get('url', '')
                if not essay_url:
                    continue
                
                essay_html = self.fetch(essay_url)
                if not essay_html:
                    continue
                
                essay = self.parse_essay_page(essay_html, essay_url)
                if essay and essay.get('body'):
                    essays.append(essay)
                    self.logger.info(f'[{self.site_name}] Parsed: {essay["title"][:30]}')
        
        return essays
