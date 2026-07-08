# ========================================
# 站点配置模板
# ========================================
# 复制此文件并重命名（如：new_site.py），然后填写对应配置。
# 新增网站时无需修改其他模块，保持低耦合。

from modules.spider_base import SpiderBase
from typing import List, Dict
from bs4 import BeautifulSoup


class NewSiteSpider(SpiderBase):
    # 网站名称（必填，用于显示和日志）
    site_name = "新网站名称"

    # 网站主页URL（必填）
    site_url = "https://example.com"

    # 列表页URL（可选，默认使用site_url）
    # 如果作文列表在其他页面，填写列表页URL
    list_urls = [
        "https://example.com/essays/list",
        "https://example.com/essays/page2",
    ]

    def get_essay_list_urls(self) -> List[str]:
        """返回列表页URL列表"""
        # 默认实现：如果有list_urls属性则返回它，否则返回site_url
        return self.list_urls if hasattr(self, 'list_urls') else [self.site_url]

    def parse_list_page(self, html: str, list_url: str) -> List[Dict]:
        """
        解析列表页，提取作文详情页链接
        返回格式：[{'url': '详情页URL', 'title': '标题（可选）'}, ...]

        参数：
            html: 页面HTML内容
            list_url: 当前列表页URL（用于解析相对链接）

        示例：
            soup = self.get_soup(html)
            items = []
            for link in soup.select('a.essay-link'):
                items.append({
                    'url': self._make_absolute_url(link['href'], list_url),
                    'title': link.text.strip()
                })
            return items
        """
        soup = self.get_soup(html)
        items = []

        # TODO: 根据网站实际HTML结构填写选择器
        # 示例：假设作文链接在<div class="essay-list">下的<a>标签中
        for link in soup.select('.essay-list a'):
            href = link.get('href', '')
            if not href:
                continue
            full_url = self._make_absolute_url(href, list_url)
            items.append({
                'url': full_url,
                'title': link.get_text(strip=True)
            })

        return items

    def parse_essay_page(self, html: str, essay_url: str) -> Dict:
        """
        解析作文详情页，提取作文数据
        返回格式：{'title', 'author', 'school', 'body', 'source', 'date'}

        参数：
            html: 页面HTML内容
            essay_url: 当前详情页URL

        示例：
            soup = self.get_soup(html)
            title = soup.select_one('h1.title').text
            author = soup.select_one('.author').text
            body = soup.select_one('.content').text
            return self.make_essay(title=title, author=author, body=body, source=essay_url)
        """
        soup = self.get_soup(html)

        # TODO: 根据网站实际HTML结构填写选择器
        title = ''
        author = ''
        school = ''
        body = ''
        date = ''

        # 示例：假设标题在<h1>，作者在.author，正文在.content
        title_elem = soup.select_one('h1')
        if title_elem:
            title = title_elem.get_text(strip=True)

        author_elem = soup.select_one('.author')
        if author_elem:
            author = author_elem.get_text(strip=True)

        school_elem = soup.select_one('.school')
        if school_elem:
            school = school_elem.get_text(strip=True)

        body_elem = soup.select_one('.essay-content')
        if body_elem:
            body = body_elem.get_text(separator='\n', strip=True)

        date_elem = soup.select_one('.publish-date')
        if date_elem:
            date = date_elem.get_text(strip=True)

        return self.make_essay(
            title=title,
            author=author,
            school=school,
            body=body,
            source=essay_url,
            date=date
        )

    def _make_absolute_url(self, href: str, base_url: str) -> str:
        """将相对URL转换为绝对URL"""
        from urllib.parse import urljoin
        return urljoin(base_url, href)


# ========================================
# 扩展说明
# ========================================
"""
1. 新增网站步骤：
   a) 复制此模板文件到 spiders/ 目录
   b) 重命名为网站简称（如：nhk_news.py）
   c) 填写 site_name 和 site_url
   d) 实现 parse_list_page 和 parse_essay_page 方法
   e) 运行程序，SpiderManager 会自动加载

2. 网站改版维护：
   - 当网站HTML结构变化时，只需修改对应Spider文件
   - 其他网站不受影响
   - 无需修改核心模块

3. 复杂情况处理：
   - 多页列表：在 list_urls 中添加所有列表页URL
   - PDF作文：SpiderBase 已自动处理，无需额外代码
   - 动态加载：SpiderBase 会自动启用 Playwright
   - 纵排文本：SpiderBase 会自动转换为横排

4. 测试方法：
   spider = NewSiteSpider()
   essays = spider.crawl()
   for essay in essays:
       print(essay['title'], essay['author'])
"""