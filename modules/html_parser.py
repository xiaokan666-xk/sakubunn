from bs4 import BeautifulSoup
import re


class HTMLParser:
    def __init__(self):
        pass

    def parse_list_page(self, html, list_selector):
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        for element in soup.select(list_selector):
            title_tag = element.find(['a', 'h1', 'h2', 'h3', 'h4'])
            if title_tag:
                url = title_tag.get('href', '')
                title = title_tag.get_text(strip=True)
                if url and title:
                    items.append({'title': title, 'url': url})
        return items

    def parse_detail_page(self, html, title_selector, content_selector):
        soup = BeautifulSoup(html, 'html.parser')
        
        title = ''
        if title_selector:
            title_element = soup.select_one(title_selector)
            if title_element:
                title = title_element.get_text(strip=True)
        
        content = ''
        if content_selector:
            content_element = soup.select_one(content_selector)
            if content_element:
                for tag in content_element(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                content = content_element.get_text('\n', strip=True)
                content = self._clean_text(content)
        
        return {'title': title, 'content': content}

    def _clean_text(self, text):
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.strip()
        return text

    def extract_links(self, html, pattern=None):
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if pattern:
                if re.search(pattern, href):
                    links.append(href)
            else:
                links.append(href)
        return links

    def extract_images(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        for img in soup.find_all('img', src=True):
            images.append(img['src'])
        return images

    def extract_pdf_links(self, html):
        return self.extract_links(html, r'\.pdf$')
