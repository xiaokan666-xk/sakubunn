import re
from typing import List, Dict
from urllib.parse import urljoin
from modules.spider_base import SpiderBase


class AnshinSpider(SpiderBase):
    site_name = "あんしん財団こども作文コンクール"
    site_url = "https://www.anshin-zaidan.or.jp/about/csr/sakubun/"
    
    LIST_URLS = [
        "https://www.anshin-zaidan.or.jp/about/csr/sakubun/",
    ]
    
    def get_essay_list_urls(self) -> List[str]:
        return self.LIST_URLS
    
    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        soup = self.get_soup(html)
        items = []
        
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            headers = []
            header_row = rows[0]
            for th in header_row.find_all(['th', 'td']):
                headers.append(th.get_text(strip=True))
            
            has_school = any('学校' in h for h in headers)
            has_name = any('氏名' in h for h in headers)
            has_title = any('タイトル' in h for h in headers)
            
            if not (has_school and has_name and has_title):
                continue
            
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                school_info = cells[0].get_text(strip=True)
                name_info = cells[1].get_text(strip=True)
                title_text = cells[2].get_text(strip=True)
                
                pdf_link = None
                for a in cells[2].find_all('a', href=True):
                    if a['href'].endswith('.pdf') and 'sakuhin' in a['href']:
                        pdf_link = urljoin(list_url, a['href'])
                        break
                
                if pdf_link:
                    items.append({
                        'title': title_text,
                        'url': pdf_link,
                        'school': school_info,
                        'author': name_info,
                    })
        
        self.logger.info(f'[あんしん財団] 发现 {len(items)} 篇作文')
        return items
    
    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        return {}
