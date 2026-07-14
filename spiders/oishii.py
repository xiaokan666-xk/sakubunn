import re
import logging
from typing import List, Dict
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from modules.spider_base import SpiderBase


class OishiiSpider(SpiderBase):
    """
    おいしい記憶コンテスト网站爬虫

    网站结构：
    - 入口：https://www.yomiuri.co.jp/adv/oishiikioku/archive/16/essay01.html
    - 左侧导航 #archive_menu 列出第1~16回
    - 每回首页左侧展开显示该回次所有作文链接
    - 每篇作文独立页面，URL模式因回次而异
    - 标题+作者有两种HTML结构：
      结构A（早期回次）：#title img 的 alt 属性
      结构B（后期回次）：#title 内文本（含 ruby 注音）
    - 正文在 #text p 标签中
    """

    site_name = "おいしい記憶コンテスト"
    site_url = "https://www.yomiuri.co.jp/adv/oishiikioku/archive/16/essay01.html"

    LIST_URLS = [
        "https://www.yomiuri.co.jp/adv/oishiikioku/archive/16/essay01.html",
    ]

    def _extract_text_with_ruby(self, element) -> str:
        """从元素中提取文本，移除 ruby 注音，保留全角空格"""
        if element is None:
            return ''
        copy = BeautifulSoup(str(element), 'html.parser').find()
        if copy is None:
            return ''
        for tag in copy.find_all(['rt', 'rp']):
            tag.decompose()
        text = copy.get_text(separator=' ', strip=True)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def get_essay_list_urls(self) -> List[str]:
        return self.LIST_URLS

    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        """
        解析入口页面，返回所有回次的首页URL
        """
        soup = self.get_soup(html)
        items = []
        seen = set()

        menu = soup.find('div', id='archive_menu')
        if not menu:
            self.logger.warning('[おいしい記憶] 未找到左侧导航 #archive_menu')
            return items

        # 提取所有回次：包括链接（其他回次）和非链接（当前回次）
        for div in menu.find_all('div', class_='number'):
            text = div.get_text(strip=True)
            if not text:
                continue
            if not re.search(r'第[一二三四五六七八九十０１２３４５６７８９\d]+回', text):
                continue

            a = div.find('a', href=True)
            if a:
                full_url = urljoin(list_url, a['href'])
            else:
                # 当前回次，使用 list_url
                full_url = list_url

            if full_url in seen:
                continue
            seen.add(full_url)
            items.append({
                'title': text,
                'url': full_url,
            })

        self.logger.info(f'[おいしい記憶] 发现 {len(items)} 个回次页面')
        return items

    def parse_round_page(self, html: str, round_url: str) -> List[Dict]:
        """
        解析回次首页，返回该回次的所有作文链接
        从 #archive_menu 中的 dl > dd 提取
        """
        soup = self.get_soup(html)
        items = []
        seen = set()

        menu = soup.find('div', id='archive_menu')
        if not menu:
            return items

        for dd in menu.find_all('dd'):
            a = dd.find('a', href=True)
            if not a:
                continue
            href = a['href']
            title = a.get_text(strip=True)
            if not title:
                continue

            # 提取作者
            author = ''
            name_span = dd.find('span', class_='archive_name')
            if name_span:
                author = name_span.get_text(strip=True)

            full_url = urljoin(round_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            items.append({
                'title': title,
                'author': author,
                'url': full_url,
            })

        self.logger.info(f'[おいしい記憶] {round_url} 发现 {len(items)} 篇作文')
        return items

    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        """
        解析作文详情页

        结构A（早期回次，如第2回）：
        <div id="title">
            <img src="..." alt="キッコーマン賞「おばあちゃんの保存食」中立 あきさん（東京都）" />
        </div>
        <div id="text"><p>...</p></div>

        结构B（后期回次，如第15回）：
        <div id="title">
            <span class="red">■小学校高学年の部（作文）<br/>優秀賞</span><br/>
            <span class="F12">「ひいおじいちゃんのさくらんぼ」</span>
            <ruby>鹿山　芭<rp>（</rp><rt>かやま　はな</rt><rp>）</rp></ruby>さん（福島県・１１歳）
            <p class="gakunen">会津若松市立門田小学校　６年</p>
        </div>
        <div id="text"><p>...</p></div>
        """
        soup = self.get_soup(html)

        essay_div = soup.find('div', id='essay')
        if not essay_div:
            essay_div = soup

        title = ''
        author = ''
        school = ''
        award = ''

        title_div = essay_div.find('div', id='title')
        if title_div:
            # 尝试结构A：img alt
            # 可能有多个img，找到包含作文标题（有「」）的那个
            target_img = None
            for img in title_div.find_all('img'):
                alt = img.get('alt', '')
                if '「' in alt and '」' in alt:
                    target_img = img
                    break
            
            # 如果没有找到带「」的img，使用第一个img
            if not target_img:
                target_img = title_div.find('img')
            
            if target_img:
                alt = target_img.get('alt', '')
                # 格式：奖项「标题」作者さん（都道府県）学校
                m = re.search(r'[「]([^」]+)[」]', alt)
                if m:
                    title = m.group(1)
                # 作者：标题后的 某某さん（...）部分
                m2 = re.search(r'[」]\s*(.+?さん\s*[（\(].*?[）\)])', alt)
                if m2:
                    author = m2.group(1).strip()
                # 奖项：标题前的文本（移除 ■）
                m3 = re.search(r'^(.*?)[「]', alt)
                if m3:
                    award = m3.group(1).strip().replace('■', '')
                # 学校：作者信息后的文本，匹配学校名模式
                if author:
                    m4 = re.search(re.escape(author) + r'\s*([^\「」]+)', alt)
                    if m4:
                        school_text = m4.group(1).strip()
                        if school_text and school_text not in author:
                            school = school_text
            else:
                # 结构B：文本内容（含 ruby）
                # 标题从 span.F12 提取
                span_f12 = title_div.find('span', class_='F12')
                if span_f12:
                    title = span_f12.get_text(strip=True).strip('「」')

                # 奖项从 span.red 提取（移除 ruby 和 ■）
                span_red = title_div.find('span', class_='red')
                if span_red:
                    award = self._extract_text_with_ruby(span_red)
                    award = award.replace('■', '').strip()

                # 作者：复制 title_div，移除 span 和 p 元素，提取剩余文本
                title_copy = BeautifulSoup(str(title_div), 'html.parser').find()
                for tag in title_copy.find_all(['span', 'p']):
                    tag.decompose()
                author_text = self._extract_text_with_ruby(title_copy)
                # 清理多余文本，提取 某某さん（...）
                m = re.search(r'(.+?さん\s*[（\(].*?[）\)])', author_text)
                if m:
                    author = m.group(1).strip()

                # 学校
                gakunen = title_div.find('p', class_='gakunen')
                if gakunen:
                    school = gakunen.get_text(strip=True)

        # 提取正文
        body = ''
        text_div = essay_div.find('div', id='text')
        if text_div:
            paragraphs = []
            for p in text_div.find_all('p'):
                p_text = p.get_text(strip=True)
                if p_text:
                    paragraphs.append(p_text)
            body = '\n'.join(paragraphs)

        # 如果标题为空，尝试从页面 title 提取
        if not title and soup.title:
            title_text = soup.title.get_text(strip=True)
            m = re.search(r'[「]([^」]+)[」]', title_text)
            if m:
                title = m.group(1)

        # 组装 author（加入奖项信息）
        full_author = author
        if award and author:
            full_author = f'{award} {author}'
        elif award:
            full_author = award

        return self.make_essay(
            title=title,
            author=full_author,
            school=school,
            body=body,
            source=essay_url,
            date='',
        )

    def crawl(self, max_count=None, essay_exists_fn=None, full_mode: bool = False) -> List[Dict]:
        """
        重写抓取流程：
        1. 访问入口页面，提取所有回次首页URL
        2. 遍历每个回次首页，提取该回次的所有作文URL
        3. 访问每篇作文页面，提取内容
        """
        essays = []
        self._failures = []
        list_urls = self.get_essay_list_urls()
        self.logger.info(f'[{self.site_name}] 开始抓取，full_mode={full_mode}')

        for list_url in list_urls:
            html = self.fetch(list_url)
            if not html:
                self._record_failure(list_url, 'LIST_FETCH_FAILED', '入口页面抓取失败')
                continue

            try:
                round_items = self.parse_list_page(html, list_url)
            except Exception as e:
                self._record_failure(list_url, 'LIST_PARSE_EXCEPTION', f'入口页面解析异常: {str(e)}')
                round_items = []

            if not round_items:
                self._record_failure(list_url, 'PARSE_EMPTY', 'parse_list_page 返回空')
                continue

            self.logger.info(f'[{self.site_name}] 发现 {len(round_items)} 个回次页')

            # 遍历每个回次页
            for round_item in round_items:
                round_url = round_item.get('url', '')
                if not round_url:
                    continue

                round_html = self.fetch(round_url)
                if not round_html:
                    self._record_failure(round_url, 'ROUND_FETCH_FAILED', '回次页抓取失败')
                    continue

                try:
                    essay_items = self.parse_round_page(round_html, round_url)
                except Exception as e:
                    self._record_failure(round_url, 'ROUND_PARSE_EXCEPTION', f'回次页解析异常: {str(e)}')
                    essay_items = []

                if not essay_items:
                    continue

                # 遍历每篇作文
                for essay_item in essay_items:
                    if max_count and len(essays) >= max_count:
                        break

                    essay_url = essay_item.get('url', '')
                    if not essay_url:
                        continue

                    # 增量模式：跳过已存在的URL
                    if not full_mode and essay_exists_fn and essay_exists_fn(essay_url):
                        self.logger.info(f'[{self.site_name}] 跳过已存在: {essay_url}')
                        continue

                    essay_html = self.fetch(essay_url)
                    if not essay_html:
                        self._record_failure(essay_url, 'ESSAY_FETCH_FAILED', '作文页抓取失败')
                        continue

                    try:
                        essay = self.parse_essay_page(essay_html, essay_url)
                    except Exception as e:
                        self._record_failure(essay_url, 'ESSAY_PARSE_EXCEPTION', f'详情页解析异常: {str(e)}')
                        essay = None

                    if essay and essay.get('body'):
                        essays.append(essay)
                        self.logger.info(f'[{self.site_name}] 抓取成功: {essay["title"][:30]}')
                    elif essay:
                        self._record_failure(essay_url, 'PARSE_EMPTY', f'正文为空: title={essay.get("title", "")}')

        return essays
