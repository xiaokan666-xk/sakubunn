import re
import logging
import os
import tempfile
import ssl
from typing import List, Dict
from urllib.parse import urljoin
from modules.spider_base import SpiderBase


class TsurezureSpider(SpiderBase):
    """
    徒然草エッセイ大賞网站爬虫

    网站结构（三层）：
    1. 首页 https://www.tsurezure-essay.jp/archives.html
       列出第1回～第9回的回次链接
    2. 回次页 https://www.tsurezure-essay.jp/archives/{回次}.html
       列出各部（一般の部/中学生の部/小学生の部）的获奖作品
       链接文本格式：「标题」作者（学校・都道府県）
    3. 作文详情页 https://www.tsurezure-essay.jp/archives/{回次}/{文件名}.html
       包含奖项（大賞/優秀賞/佳作）、标题、作者信息、正文
    """

    site_name = "徒然草エッセイ大賞"
    site_url = "https://www.tsurezure-essay.jp/archives.html"

    LIST_URLS = [
        "https://www.tsurezure-essay.jp/archives.html",
    ]

    def _extract_text_from_p(self, p) -> str:
        """
        从<p>标签中提取文本，保留<br/>换行和段落开头全角空格，移除ruby注音等标签
        """
        from bs4 import BeautifulSoup
        # 复制p标签避免修改原始树
        p_copy = BeautifulSoup(str(p), 'html.parser').p
        # 先移除ruby中的rt和rp节点（注音和括号）
        for tag in p_copy.find_all(['rt', 'rp']):
            tag.decompose()
        # 获取处理后的HTML内容（不strip，保留开头全角空格）
        html_content = p_copy.decode_contents()
        # 将<br/>和<br>替换为换行符
        html_content = html_content.replace('<br/>', '\n').replace('<br>', '\n')
        # 移除所有剩余HTML标签
        text = re.sub(r'<[^>]+>', '', html_content)
        # 只清理ASCII多余空白，保留全角空格
        text = re.sub(r'[ \t]+', ' ', text)
        # 清理每行：只去掉ASCII空白，保留全角空格缩进
        lines = []
        for line in text.split('\n'):
            # 去掉右端ASCII空白
            line = line.rstrip(' \t')
            # 去掉左端ASCII空白，但保留全角空格（日语段落缩进）
            line = line.lstrip(' \t')
            if line:
                lines.append(line)
        return '\n'.join(lines)

    def get_essay_list_urls(self) -> List[str]:
        return self.LIST_URLS

    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        """
        解析首页，返回所有回次页面
        """
        soup = self.get_soup(html)
        items = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)

            if not text:
                continue
            if not re.search(r'第[一二三四五六七八九十]+回', text):
                continue
            if 'テーマ' not in text and '応募数' not in text:
                continue

            full_url = urljoin(list_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            items.append({
                'title': text,
                'url': full_url,
            })

        self.logger.info(f'[徒然草] 发现 {len(items)} 个回次页面')
        return items

    def parse_round_page(self, html: str, round_url: str) -> List[Dict]:
        """
        解析回次页面，返回所有作文详情页链接
        链接文本格式：「标题」作者（学校・都道府県）
        """
        soup = self.get_soup(html)
        items = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)

            if not text or not href:
                continue
            if href.startswith('#') or 'twitter' in href or 'facebook' in href:
                continue
            if 'senpyou' in href:
                continue
            if text in ['シェア', 'ツイート']:
                continue
            if '「' not in text or '」' not in text:
                continue

            full_url = urljoin(round_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            title_author = self._parse_link_text(text)
            items.append({
                'title': title_author['title'],
                'author': title_author['author'],
                'url': full_url,
            })

        self.logger.info(f'[徒然草] 回次页 {round_url} 发现 {len(items)} 篇作文')
        return items

    def _parse_link_text(self, text: str) -> Dict:
        """
        解析链接文本，提取标题和作者
        格式：「标题」作者姓名（学校 年级・都道府県）
        """
        result = {'title': '', 'author': ''}

        title_match = re.search(r'「([^」]+)」', text)
        if title_match:
            result['title'] = title_match.group(1).strip()

        author_match = re.search(r'」([^（]+)', text)
        if author_match:
            result['author'] = author_match.group(1).strip()

        return result

    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        """
        解析作文详情页

        实际HTML结构（两种）：

        结构A（旧式/早期回次）：
        <div id="archives">
            <h2>大賞</h2>             <- 奖项
            <h3>よう、虫</h3>          <- 标题
            <p>千葉県柏市</p>          <- 作者地址
            <p>生天目  咲樹</p>         <- 作者姓名
            <p>（17）</p>              <- 年龄
            <p>「悪魔」との...</p>      <- 正文
        </div>

        结构B（新式/第九回）：
        <div id="archives">
            <section id="archivesCon">
                <h3><img alt="中学生の部" ...></h3>
                <div class="box">
                    <h4 class="ribbon">大賞</h4>            <- 奖项
                    <dl class="name">
                        <dt>延長線上の私</dt>                <- 标题
                        <dd>学校法人市川学園 市川中学校 1年　宮下 英美理</dd>  <- 作者
                    </dl>
                    <p>...正文...</p>
                </div>
            </section>
        </div>
        """
        soup = self.get_soup(html)

        # 优先使用 #archives 容器
        archives = soup.find('div', id='archives')
        if not archives:
            archives = soup.find('div', class_='box')
        if not archives:
            archives = soup

        award = ''
        title = ''
        author_info = ''
        body_paragraphs = []

        # ===== 尝试结构B：使用 dl.name =====
        dl_name = archives.find('dl', class_='name')

        if dl_name:
            # 结构B（有dl.name的页面）

            # 提取奖项：先找 h4.ribbon，没有则用 title 标签
            h4_ribbon = archives.find('h4', class_='ribbon')
            if h4_ribbon:
                award_text = h4_ribbon.get_text(strip=True)
                if award_text in ['大賞', '優秀賞', '佳作']:
                    award = award_text

            # 如果没找到奖项，尝试从 title 标签
            if not award and soup.title:
                title_text = soup.title.get_text(strip=True)
                m = re.search(r'「大賞」|「優秀賞」|「佳作」', title_text)
                if m:
                    award = m.group(0).strip('「」')

            dt = dl_name.find('dt')
            if dt:
                title = dt.get_text(strip=True)

            dd = dl_name.find('dd')
            if dd:
                author_info = dd.get_text(' ', strip=True)
                # 清理ruby标签产生的注释字符
                author_info = re.sub(r'[\(（][^）\)]*[\)）]', '', author_info).strip()

            # 提取正文：archives下所有p标签
            # 先处理HTML：保留<br/>换行，移除ruby注音等标签
            for p in archives.find_all('p'):
                p_text = self._extract_text_from_p(p)
                if p_text and len(p_text) > 10:
                    body_paragraphs.append(p_text)
        else:
            # ===== 结构A：使用 h3 / 多个p标签 =====
            # 提取奖项
            for h in archives.find_all(['h2', 'h3', 'h4']):
                h_text = h.get_text(strip=True)
                if h_text in ['大賞', '優秀賞', '佳作']:
                    award = h_text
                    break

            # 提取标题
            for h in archives.find_all(['h2', 'h3', 'h4']):
                h_text = h.get_text(strip=True)
                if h_text in ['大賞', '優秀賞', '佳作', 'シェア', 'ツイート']:
                    continue
                if h.find('img'):
                    continue
                if '作品一覧' in h_text or '徒然草' in h_text:
                    continue
                if 1 <= len(h_text) <= 50:
                    title = h_text
                    break

            # 备选：从title标签提取
            if not title and soup.title:
                title_text = soup.title.get_text(strip=True)
                m = re.search(r'「([^」]+)」', title_text)
                if m:
                    title = m.group(1).strip()

            # 提取作者信息（标题后的几个p标签）
            if title:
                all_p = archives.find_all('p')
                author_p_list = []
                body_started = False

                for p in all_p:
                    # 先处理HTML：保留<br/>换行，移除ruby注音等标签
                    p_text = self._extract_text_from_p(p)
                    if not p_text:
                        continue
                    # 跳过奖项
                    if p_text in ['大賞', '優秀賞', '佳作']:
                        continue
                    # 跳过标题
                    if p_text == title:
                        continue
                    # 跳过SNS
                    if p_text in ['シェア', 'ツイート']:
                        continue
                    # 跳过版权
                    if p_text.startswith('©') or 'All Rights Reserved' in p_text:
                        continue
                    # 跳过 :: 分类
                    if '::' in p_text:
                        continue

                    # 是否是作者信息（短文本）
                    is_short = len(p_text) <= 50
                    has_address = re.search(r'[都道府県市町村区町]', p_text) is not None
                    has_school = re.search(r'(学校|中学校|高等学校|学園)', p_text) is not None
                    has_age = re.match(r'^[\(（]\d+[\)）]$', p_text) is not None
                    is_name_like = (is_short and
                                    re.search(r'[\u4e00-\u9fff]', p_text) and
                                    len(p_text) <= 30)

                    if not body_started and (has_address or has_school or has_age or is_name_like):
                        author_p_list.append(p_text)
                    else:
                        # 这是正文
                        body_started = True
                        if len(p_text) > 10:
                            body_paragraphs.append(p_text)

                author_info = ' '.join(author_p_list).strip()

        body = '\n'.join(body_paragraphs).strip()

        return self.make_essay(
            title=title,
            author=author_info,
            body=body,
            source=essay_url,
            date='',
        )

    def crawl(self, max_count=None, essay_exists_fn=None, full_mode: bool = False) -> List[Dict]:
        """
        重写抓取流程，支持三层结构：
        首页 → 回次页 → 作文详情页
        """
        essays = []
        self._failures = []
        list_urls = self.get_essay_list_urls()
        self.logger.info(f'[{self.site_name}] 开始抓取，full_mode={full_mode}')

        for list_url in list_urls:
            html = self.fetch(list_url)
            if not html:
                self._record_failure(list_url, 'LIST_FETCH_FAILED', '首页抓取失败')
                continue

            try:
                round_items = self.parse_list_page(html, list_url)
            except Exception as e:
                self._record_failure(list_url, 'LIST_PARSE_EXCEPTION', f'首页解析异常: {str(e)}')
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
