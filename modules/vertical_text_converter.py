import re
import logging
from typing import List, Dict


class VerticalTextConverter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def is_vertical(self, text: str) -> bool:
        if not text:
            return False
        
        total_chars = len(re.sub(r'\s', '', text))
        if total_chars < 10:
            return False
        
        lines = [l for l in text.split('\n') if l.strip()]
        if len(lines) < 2:
            return False
        
        short_lines = sum(1 for l in lines if len(l) <= 2)
        return short_lines / len(lines) > 0.3
    
    def is_vertical_html(self, html: str) -> bool:
        vertical_indicators = [
            r'writing-mode\s*:\s*vertical',
            r'-webkit-writing-mode\s*:\s*vertical',
            r'tategaki',
            r'縦書き',
            r'writing-mode:\s*vertical-rl',
        ]
        for pattern in vertical_indicators:
            if re.search(pattern, html, re.IGNORECASE):
                return True
        return False
    
    def convert_vertical_to_horizontal(self, text: str) -> str:
        if not self.is_vertical(text):
            return text
        
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if not lines:
            return text
        
        max_len = max(len(l) for l in lines)
        
        padded_lines = [l.ljust(max_len, '　') for l in lines]
        
        horizontal_chars = []
        for col_idx in range(max_len):
            column_chars = []
            for line in padded_lines:
                if col_idx < len(line) and line[col_idx] != '　':
                    column_chars.append(line[col_idx])
            if column_chars:
                horizontal_chars.append(''.join(column_chars))
        
        result = '\n'.join(horizontal_chars)
        self.logger.debug(f'Converted vertical text: {len(lines)} lines -> {len(horizontal_chars)} lines')
        return result
    
    def convert_vertical_ocr_items(self, items: List[Dict]) -> str:
        if not items:
            return ''
        
        if not all('box' in item for item in items):
            return '\n'.join(item.get('text', '') for item in items)
        
        boxes = [item['box'] for item in items]
        widths = [max(p[0] for p in b) - min(p[0] for p in b) for b in boxes]
        heights = [max(p[1] for p in b) - min(p[1] for p in b) for b in boxes]
        
        avg_w = sum(widths) / len(widths) if widths else 0
        avg_h = sum(heights) / len(heights) if heights else 0
        
        is_vert = avg_h > avg_w * 1.2
        
        if not is_vert:
            items_sorted = sorted(items, key=lambda x: (
                sum(p[1] for p in x['box']) / 4,
                sum(p[0] for p in x['box']) / 4
            ))
        else:
            items_sorted = sorted(items, key=lambda x: (
                sum(p[0] for p in x['box']) / 4,
                -sum(p[1] for p in x['box']) / 4
            ))
        
        return '\n'.join(item.get('text', '') for item in items_sorted)
