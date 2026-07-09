import logging
import time
from typing import Optional


class PlaywrightFetcher:
    def __init__(self, headless=True, timeout=30):
        self.headless = headless
        self.timeout = timeout * 1000
        self.logger = logging.getLogger(__name__)
        self._browser = None
        self._playwright = None
        self._available = None
    
    def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from playwright.sync_api import sync_playwright
            self._available = True
        except ImportError:
            self.logger.warning('Playwright not installed. Run: pip install playwright && playwright install chromium')
            self._available = False
        return self._available
    
    def fetch(self, url: str, wait_selector: str = None, wait_time: int = 2) -> Optional[str]:
        if not self._check_available():
            return None
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors',
                        '--allow-insecure-localhost',
                        '--disable-web-security',
                        '--no-sandbox',
                        '--disable-setuid-sandbox'
                    ]
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
                    locale='ja-JP'
                )
                page = context.new_page()
                page.set_default_timeout(self.timeout)
                
                try:
                    page.goto(url, wait_until='networkidle', timeout=self.timeout)
                    
                    if wait_selector:
                        try:
                            page.wait_for_selector(wait_selector, timeout=self.timeout)
                        except Exception:
                            self.logger.debug(f'Wait selector not found: {wait_selector}')
                    
                    if wait_time > 0:
                        time.sleep(wait_time)
                    
                    html = page.content()
                    self.logger.info(f'Playwright fetched: {url}')
                    return html
                finally:
                    context.close()
                    browser.close()
        except Exception as e:
            self.logger.error(f'Playwright fetch failed: {url} - {e}')
            return None
    
    def fetch_binary(self, url: str) -> Optional[bytes]:
        if not self._check_available():
            return None
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors',
                        '--allow-insecure-localhost',
                        '--disable-web-security',
                        '--no-sandbox',
                        '--disable-setuid-sandbox'
                    ]
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                try:
                    response = page.goto(url, timeout=self.timeout)
                    if response:
                        return response.body()
                finally:
                    context.close()
                    browser.close()
        except Exception as e:
            self.logger.error(f'Playwright binary fetch failed: {url} - {e}')
            return None
        return None
