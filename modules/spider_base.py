import re
import logging
import requests
import os
import tempfile
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from urllib.parse import urljoin
from modules.playwright_fetcher import PlaywrightFetcher
from modules.paddle_ocr import PaddleOCREngine
from modules.pdf_smart_parser import PDFSmartParser
from modules.vertical_text_converter import VerticalTextConverter
from modules.error_tracker import ErrorTracker


CRAWL_TYPE_HTML = 'A'
CRAWL_TYPE_HTML_MULTI = 'B'
CRAWL_TYPE_PDF_TEXT = 'C'
CRAWL_TYPE_PDF_OCR = 'D'


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
        self.playwright = PlaywrightFetcher()
        self.ocr_engine = PaddleOCREngine()
        self.pdf_parser = PDFSmartParser(ocr_engine=self.ocr_engine)
        self.vertical_converter = VerticalTextConverter()
        self.error_tracker = ErrorTracker()
        self._temp_dir = None
        self._failures = []
        self._resource_cache = None
    
    @property
    def temp_dir(self):
        if self._temp_dir is None:
            from config import DATA_DIR
            self._temp_dir = os.path.join(DATA_DIR, 'temp')
            os.makedirs(self._temp_dir, exist_ok=True)
        return self._temp_dir
    
    def _record_failure(self, url: str, error_type: str, error_msg: str):
        self._failures.append({
            'site_name': self.site_name,
            'site_url': self.site_url,
            'url': url,
            'error_type': error_type,
            'error_msg': error_msg,
        })
        self.error_tracker.record_error(
            site_name=self.site_name,
            site_url=self.site_url,
            url=url,
            error_type=error_type,
            error_msg=error_msg
        )
    
    def get_failures(self) -> List[Dict]:
        return self._failures
    
    def fetch(self, url: str, timeout: int = 30, use_playwright_on_fail: bool = True) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            html = response.text
            
            if self._is_meaningful_html(html) or not use_playwright_on_fail:
                return html
            
            self.logger.info(f'HTML empty/poor, trying Playwright: {url}')
            pw_html = self.playwright.fetch(url)
            if pw_html:
                return pw_html
            
            self._record_failure(url, 'PLAYWRIGHT_FALLBACK_FAILED', 'requests内容不完整且Playwright备选也失败')
            return html
        except requests.RequestException as e:
            self.logger.warning(f'Requests fetch failed [{self.site_name}] {url}: {e}')
            if use_playwright_on_fail:
                self.logger.info(f'Falling back to Playwright: {url}')
                pw_html = self.playwright.fetch(url)
                if pw_html:
                    return pw_html
                self._record_failure(url, 'FETCH_FAILED', f'requests和Playwright均失败: {str(e)}')
                return None
            self._record_failure(url, 'FETCH_FAILED', str(e))
            return None
    
    def _is_meaningful_html(self, html: str) -> bool:
        if not html:
            return False
        if len(html) < 500:
            return False
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(strip=True)
        if len(text) < 100:
            return False
        if soup.find('html') is None:
            return False
        return True
    
    def fetch_binary(self, url: str, timeout: int = 30) -> Optional[bytes]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            self.logger.error(f'Fetch binary failed [{self.site_name}] {url}: {e}')
            self._record_failure(url, 'BINARY_FETCH_FAILED', str(e))
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
    
    def detect_crawl_type(self, url: str) -> str:
        if re.search(r'\.pdf(\?|$)', url, re.IGNORECASE):
            return CRAWL_TYPE_PDF_TEXT
        
        html = self.fetch(url, use_playwright_on_fail=False)
        if not html:
            return CRAWL_TYPE_HTML
        
        soup = self.get_soup(html)
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
        if pdf_links:
            return CRAWL_TYPE_HTML_MULTI
        
        return CRAWL_TYPE_HTML
    
    def is_pdf_url(self, url: str) -> bool:
        return bool(re.search(r'\.pdf(\?|$)', url, re.IGNORECASE))
    
    def set_resource_cache(self, cache):
        self._resource_cache = cache

    def handle_pdf_url(self, pdf_url: str) -> Optional[Dict]:
        self.logger.info(f'Handling PDF: {pdf_url}')

        if self._resource_cache and self._resource_cache.resource_exists(pdf_url):
            cached = self._resource_cache.get_processed_resource(pdf_url)
            if cached and cached['status'] == 'success':
                self.logger.info(f'[{self.site_name}] Using cached PDF result: {pdf_url}')
                return {
                    'title': '',
                    'author': '',
                    'school': '',
                    'body': cached.get('processed_content', ''),
                    'source': pdf_url,
                    'date': '',
                    'site': self.site_name
                }

        content = self.fetch_binary(pdf_url)
        if not content:
            content = self.playwright.fetch_binary(pdf_url)
        if not content:
            self._record_failure(pdf_url, 'PDF_DOWNLOAD_FAILED', '无法下载PDF文件')
            return None

        filename = re.sub(r'[^\w\-_\.]', '_', os.path.basename(pdf_url.split('?')[0])) or 'temp.pdf'
        pdf_path = os.path.join(self.temp_dir, filename)

        with open(pdf_path, 'wb') as f:
            f.write(content)

        try:
            result = self.pdf_parser.parse(pdf_path)
            if result:
                result['source'] = pdf_url
                result['site'] = self.site_name
                if self._resource_cache:
                    self._resource_cache.insert_processed_resource(
                        resource_url=pdf_url,
                        resource_type='pdf',
                        content=content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else str(content),
                        processed_content=result.get('body', '')
                    )
                if not result.get('body'):
                    self._record_failure(pdf_url, 'PDF_PARSE_EMPTY', 'PDF解析后正文为空')
            return result
        except Exception as e:
            self._record_failure(pdf_url, 'PDF_PARSE_FAILED', str(e))
            return None
        finally:
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
    
    def handle_vertical_text(self, html: str, text: str) -> str:
        if self.vertical_converter.is_vertical_html(html):
            self.logger.info(f'[{self.site_name}] Detected vertical HTML layout')
            return self.vertical_converter.convert_vertical_to_horizontal(text)
        if self.vertical_converter.is_vertical(text):
            self.logger.info(f'[{self.site_name}] Detected vertical text layout')
            return self.vertical_converter.convert_vertical_to_horizontal(text)
        return text
    
    def get_essay_list_urls(self) -> List[str]:
        return [self.site_url]
    
    @abstractmethod
    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        pass
    
    def crawl(self, max_count: int = None, essay_exists_fn=None, full_mode: bool = False) -> List[Dict]:
        essays = []
        self._failures = []
        list_urls = self.get_essay_list_urls()
        self.logger.info(f'[{self.site_name}] Found {len(list_urls)} list pages, full_mode={full_mode}')

        for list_url in list_urls:
            html = self.fetch(list_url)
            if not html:
                self._record_failure(list_url, 'LIST_FETCH_FAILED', '列表页抓取失败')
                continue

            try:
                items = self.parse_list_page(html, list_url)
            except Exception as e:
                self._record_failure(list_url, 'LIST_PARSE_EXCEPTION', f'列表页解析异常: {str(e)}')
                items = []

            if not items:
                self._record_failure(list_url, 'PARSE_EMPTY', 'parse_list_page returned empty - 该网站页面可能已更新，请检查抓取规则')
                continue

            self.logger.info(f'[{self.site_name}] Found {len(items)} essay links in {list_url}')

            for item in items:
                if max_count and len(essays) >= max_count:
                    break

                essay_url = item.get('url', '')
                if not essay_url:
                    continue

                # 增量模式：跳过已存在的URL
                if not full_mode and essay_exists_fn and essay_exists_fn(essay_url):
                    self.logger.info(f'[{self.site_name}] Skip existing: {essay_url}')
                    continue

                if self.is_pdf_url(essay_url):
                    essay = self.handle_pdf_url(essay_url)
                else:
                    essay_html = self.fetch(essay_url)
                    if not essay_html:
                        continue
                    try:
                        essay = self.parse_essay_page(essay_html, essay_url)
                    except Exception as e:
                        self._record_failure(essay_url, 'ESSAY_PARSE_EXCEPTION', f'详情页解析异常: {str(e)}')
                        essay = None

                    if essay:
                        if not essay.get('body'):
                            self._record_failure(essay_url, 'PARSE_EMPTY', f'详情页正文为空 - 该网站页面可能已更新，请检查抓取规则: title={essay.get("title", "")}')
                        else:
                            essay['body'] = self.handle_vertical_text(essay_html, essay['body'])

                if essay and essay.get('body'):
                    essays.append(essay)
                    self.logger.info(f'[{self.site_name}] Parsed: {essay["title"][:30]}')

        return essays
