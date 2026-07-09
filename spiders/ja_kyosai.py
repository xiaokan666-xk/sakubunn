import re
from typing import List, Dict
from urllib.parse import urljoin
from modules.spider_base import SpiderBase


class JaKyosaiSpider(SpiderBase):
    site_name = "JA共済小中学生作文コンクール"
    site_url = "https://ja-kyosai-fukuoka.com/"

    def get_essay_list_urls(self) -> List[str]:
        return ['https://ja-kyosai-fukuoka.com/award/index/history/']

    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        soup = self.get_soup(html)
        items = []
        seen_urls = set()

        award_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/award/category/' in href:
                full_url = urljoin(list_url, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    award_links.append(full_url)

        self.logger.info(f'[JA共済] 发现 {len(award_links)} 个奖项页面')

        def extract_essay_links(page_soup, base_url):
            essay_urls = []
            for a in page_soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True)
                if '作文を読む' in text and '/award/detail/' in href:
                    full_url = urljoin(base_url, href)
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        essay_urls.append(full_url)
            return essay_urls

        for award_url in award_links:
            award_html = self.fetch(award_url)
            if not award_html:
                self.logger.warning(f'[JA共済] 奖项页面抓取失败: {award_url}')
                continue

            award_soup = self.get_soup(award_html)
            year_match = re.search(r'/(\d{4})$', award_url)
            current_year = year_match.group(1) if year_match else ''

            if current_year == '2024':
                next_url = award_url.replace('/2024', '/2025')
                next_html = self.fetch(next_url)
                if next_html:
                    next_soup = self.get_soup(next_html)
                    essay_urls = extract_essay_links(next_soup, next_url)
                    for essay_url in essay_urls:
                        items.append({'title': '', 'url': essay_url})

            essay_urls = extract_essay_links(award_soup, award_url)
            for essay_url in essay_urls:
                items.append({'title': '', 'url': essay_url})

        self.logger.info(f'[JA共済] 共发现 {len(items)} 篇作文')
        return items

    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        soup = self.get_soup(html)

        title = ''
        h1 = soup.find('h1', class_='award-detail__title')
        if h1:
            title = h1.get_text(strip=True)

        author = ''
        school = ''

        name_span = soup.find('span', class_='award-winner__name')
        if name_span:
            author = name_span.get_text(strip=True).replace('\u3000', ' ')

        school_p = soup.find('p', class_='award-winner__school')
        if school_p:
            school_text = school_p.get_text(strip=True)
            if name_span:
                name_text = name_span.get_text(strip=True)
                school = school_text.replace(name_text, '').strip()
                school = school.replace('\u3000', ' ')
            else:
                school = school_text.replace('\u3000', ' ')

        body = ''
        contents_div = soup.find('div', class_='award-detail__contents')
        if contents_div:
            body = contents_div.get_text('\n', strip=True)

        if not title or not body:
            return {}

        date = ''
        year_match = re.search(r'/(\d{4})', essay_url)
        if year_match:
            date = year_match.group(1)

        return self.make_essay(
            title=title,
            author=author,
            school=school,
            body=body,
            source=essay_url,
            date=date
        )