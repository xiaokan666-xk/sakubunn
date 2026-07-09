import re
from typing import List, Dict
from urllib.parse import urljoin
from modules.spider_base import SpiderBase


class NetnfuSpider(SpiderBase):
    """
    日本福祉大学作文コンクール 抓取器

    网站结构：
    1. 首页: https://www.netnfu.ne.jp/lec/sakubun/index.html
       - 包含「過去archive」区域，有 2005-2024 年度链接
    2. 年份页: https://www.netnfu.ne.jp/lec/sakubun/YYYY/index.html
       - 列出该年度所有获奖作文
       - 每篇作文有「続きを読む」链接
    3. 作文详情页: https://www.netnfu.ne.jp/lec/sakubun/YYYY/author/
       - h3: 奖项 + 「作文标题」
       - h4[0]: 学校名 + 年级
       - h4[1]: 作者姓名
       - p标签: 作文正文（多个段落）
    """

    site_name = "日本福祉大学作文コンクール"
    site_url = "https://www.netnfu.ne.jp/lec/sakubun/index.html"

    def get_essay_list_urls(self) -> List[str]:
        return [self.site_url]

    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        """
        从首页进入年份页，再提取所有作文详情页链接

        流程：
        首页 → 過去archive → 年份页 → 「続きを読む」→ 作文详情页
        """
        soup = self.get_soup(html)
        items = []
        seen_urls = set()

        # 第一步：从首页提取年份链接
        year_links = []
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            href = a['href']
            # 匹配 "2024年度"、"2023年度" 等
            if re.search(r'\d{4}年度', text):
                full_url = urljoin(list_url, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    year_links.append(full_url)

        self.logger.info(f'[{self.site_name}] 发现 {len(year_links)} 个年份页面')

        # 第二步：进入每个年份页面，提取「続きを読む」链接
        for year_url in year_links:
            year_html = self.fetch(year_url)
            if not year_html:
                self.logger.warning(f'[{self.site_name}] 年份页抓取失败: {year_url}')
                continue

            year_soup = self.get_soup(year_html)

            for a in year_soup.find_all('a', href=True):
                text = a.get_text(strip=True)
                href = a['href']
                full_url = urljoin(year_url, href)

                if '続きを読む' in text and full_url not in seen_urls:
                    seen_urls.add(full_url)

                    # 提取作文标题：从「続きを読む」前面的 h3 标签中找「」内的内容
                    title = ''
                    prev_headings = a.find_all_previous(['h2', 'h3', 'h4'])
                    for ph in prev_headings:
                        ph_text = ph.get_text(strip=True)
                        title_match = re.search(r'「(.+?)」', ph_text)
                        if title_match:
                            title = title_match.group(1)
                            break

                    items.append({'title': title, 'url': full_url})

        self.logger.info(f'[{self.site_name}] 共发现 {len(items)} 篇作文')
        return items

    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        """
        从作文详情页提取：标题、作者、学校、正文

        页面结构：
        - h3: 奖项 + 「作文标题」
        - h4[0]: 学校名 + 年级（如"大府市立大府中学校1年"）
        - h4[1]: 作者姓名（如"木田彩花"）
        - p标签: 作文正文（多个段落）
        """
        soup = self.get_soup(html)

        # 提取标题：从 h3 标签的「」中提取
        title = ''
        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True)
            title_match = re.search(r'「(.+?)」', text)
            if title_match:
                title = title_match.group(1)
                break

        # 提取作者信息：h4 标签
        author = ''
        school = ''

        h4_tags = soup.find_all('h4')
        if len(h4_tags) >= 1:
            # 第一个 h4：学校 + 年级
            school_text = h4_tags[0].get_text(strip=True)
            # 提取学校名（到"学校"为止）
            school_match = re.search(r'(.+?学校)', school_text)
            if school_match:
                school = school_match.group(1).strip()

        if len(h4_tags) >= 2:
            # 第二个 h4：作者姓名
            author = h4_tags[1].get_text(strip=True)

        # 提取正文：所有 p 标签（排除非作文内容）
        body_paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)

            # 排除过短的段落
            if len(text) < 20:
                continue

            # 排除非作文内容
            exclude_patterns = [
                r'Copyright',
                r'著作権',
                r'前のページ',
                r'次のページ',
                r'HOME',
                r'トップ',
                r'戻る',
                r'主催.*後援',  # "主催/学校法人日本福祉大学、半田市、半田市教育委員会 後援／知多管内4市5町教育委員会"
            ]

            should_exclude = False
            for pattern in exclude_patterns:
                if re.search(pattern, text):
                    should_exclude = True
                    break

            if should_exclude:
                continue

            body_paragraphs.append(text)

        body = '\n\n'.join(body_paragraphs) if body_paragraphs else ''

        # 从 URL 中提取年份作为日期
        date = ''
        date_match = re.search(r'(\d{4})年度', essay_url)
        if date_match:
            date = date_match.group(1)

        return self.make_essay(
            title=title,
            author=author,
            school=school,
            body=body,
            source=essay_url,
            date=date
        )
