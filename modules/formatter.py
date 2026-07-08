import re
import hashlib


class Formatter:
    def __init__(self):
        pass

    def clean_content(self, content):
        content = content.strip()
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        content = re.sub(r'[\r\t]+', '\n', content)
        
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n\n'.join(cleaned_lines)

    def count_words(self, text):
        if not text:
            return 0
        jp_chars = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', text))
        en_words = len(re.findall(r'[a-zA-Z]+', text))
        return jp_chars + en_words

    def generate_unique_key(self, title, url):
        raw = f'{title}{url}'
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def format_essay(self, raw_essay):
        essay = {
            'title': raw_essay.get('title', '').strip(),
            'content': self.clean_content(raw_essay.get('content', '')),
            'source_url': raw_essay.get('source_url', ''),
            'source_name': raw_essay.get('source_name', ''),
            'category': raw_essay.get('category', ''),
            'grade': raw_essay.get('grade', ''),
            'word_count': self.count_words(raw_essay.get('content', ''))
        }
        
        essay['unique_key'] = self.generate_unique_key(essay['title'], essay['source_url'])
        
        return essay
