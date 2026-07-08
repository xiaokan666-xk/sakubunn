import re
from typing import List, Dict
from urllib.parse import urljoin
from modules.spider_base import SpiderBase


class OishiiSpider(SpiderBase):
    site_name = "おいしい記憶コンテスト"
    site_url = "https://yab.yomiuri.co.jp/adv/oishiikioku/archive/15/essay01.html"
    
    LIST_URLS = [
        "https://yab.yomiuri.co.jp/adv/oishiikioku/archive/15/essay01.html",
    ]
    
    def get_essay_list_urls(self) -> List[str]:
        return self.LIST_URLS
    
    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        soup = self.get_soup(html)
        items = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if text and ('エッセイ' in text or '作文' in text or '作品' in text or '記憶' in text) and len(text) > 3 and href != '#':
                full_url = urljoin(list_url, href)
                if full_url not in [item['url'] for item in items]:
                    items.append({'title': text, 'url': full_url})
        return items
    
    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        soup = self.get_soup(html)
        
        title = ''
        for tag in ['h1', 'h2', 'h3']:
            t = soup.find(tag)
            if t:
                title = t.get_text(strip=True)
                break
        if not title and soup.title:
            title = soup.title.get_text(strip=True)
        
        body = ''
        for tag in soup.find_all(['div', 'article', 'section']):
            text = tag.get_text('\n', strip=True)
            if len(text) > 200:
                body = text
                break
        
        if not body:
            body = soup.get_text('\n', strip=True)
        
        author_match = re.search(r'(作者|氏名|名前|ペンネーム)[：:\s]*([^\n]+)', body)
        author = author_match.group(2).strip() if author_match else ''
        
        date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', body)
        date = date_match.group(0) if date_match else ''
        
        return self.make_essay(
            title=title,
            author=author,
            body=body,
            source=essay_url,
            date=date
        )
