import os
import re
import logging
import tempfile
from typing import Optional, List, Dict


class PDFSmartParser:
    def __init__(self, ocr_engine=None):
        self.logger = logging.getLogger(__name__)
        self.ocr_engine = ocr_engine
    
    def parse(self, pdf_path: str) -> Optional[Dict]:
        from config import DATA_DIR
        
        with tempfile.TemporaryDirectory(dir=DATA_DIR) as tmpdir:
            has_text = self._has_text_layer(pdf_path)
            
            if has_text:
                self.logger.info(f'PDF has text layer: {pdf_path}')
                return self._parse_with_text_layer(pdf_path)
            else:
                self.logger.info(f'PDF needs OCR: {pdf_path}')
                return self._parse_with_ocr(pdf_path, tmpdir)
    
    def _has_text_layer(self, pdf_path: str) -> bool:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                total_chars = 0
                for page in pdf.pages:
                    text = page.extract_text() or ''
                    total_chars += len(text.strip())
                    if total_chars > 50:
                        return True
                return False
        except Exception as e:
            self.logger.error(f'Text layer check failed: {e}')
            return False
    
    def _parse_with_text_layer(self, pdf_path: str) -> Dict:
        try:
            import pdfplumber
            pages_text = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    words = page.extract_words()
                    if words:
                        is_vertical = self._detect_vertical_layout(words)
                        if is_vertical:
                            text = self._convert_vertical_words_to_text(words, page)
                        else:
                            text = page.extract_text() or ''
                    else:
                        text = page.extract_text() or ''
                    
                    if text.strip():
                        pages_text.append({
                            'page': i + 1,
                            'text': text
                        })
            
            body = self._extract_main_body(pages_text)
            meta = self._extract_metadata_from_pdf_text(body)
            
            return {
                'title': meta.get('title', ''),
                'author': meta.get('author', ''),
                'school': meta.get('school', ''),
                'body': body,
                'source': '',
                'date': meta.get('date', ''),
                'site': ''
            }
        except Exception as e:
            self.logger.error(f'PDF text parse failed: {e}')
            return None
    
    def _detect_vertical_layout(self, words) -> bool:
        if len(words) < 10:
            return False
        
        x_coords = [round(w['x0'], 1) for w in words]
        x_counts = {}
        for x in x_coords:
            x_counts[x] = x_counts.get(x, 0) + 1
        
        max_count = max(x_counts.values())
        return max_count >= 5
    
    def _convert_vertical_words_to_text(self, words, page) -> str:
        columns = {}
        
        for word in words:
            x_key = round(word['x0'], 1)
            if x_key not in columns:
                columns[x_key] = []
            columns[x_key].append((word['top'], word['text']))
        
        for x_key in columns:
            columns[x_key].sort(key=lambda item: item[0])
        
        sorted_columns = sorted(columns.keys(), reverse=True)
        
        result_lines = []
        for x_key in sorted_columns:
            line_chars = [item[1] for item in columns[x_key]]
            line = ''.join(line_chars)
            if line.strip():
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _parse_with_ocr(self, pdf_path: str, tmpdir: str) -> Optional[Dict]:
        if not self.ocr_engine or not self.ocr_engine.is_available():
            self.logger.error('OCR engine not available')
            return None
        
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(pdf_path, dpi=200, output_folder=tmpdir, fmt='jpg')
            
            pages_text = []
            for i, img in enumerate(images):
                img_path = os.path.join(tmpdir, f'page_{i+1}.jpg')
                img.save(img_path, 'JPEG')
                
                self.logger.info(f'OCR processing page {i+1}/{len(images)}')
                text = self.ocr_engine.recognize_to_text(img_path)
                if text.strip():
                    pages_text.append({
                        'page': i + 1,
                        'text': text
                    })
                
                try:
                    os.unlink(img_path)
                except Exception:
                    pass
            
            body = self._extract_main_body(pages_text)
            meta = self._extract_metadata_from_pdf_text(body)
            
            return {
                'title': meta.get('title', ''),
                'author': meta.get('author', ''),
                'school': meta.get('school', ''),
                'body': body,
                'source': '',
                'date': meta.get('date', ''),
                'site': ''
            }
        except ImportError:
            self.logger.error('pdf2image not installed. Run: pip install pdf2image')
            return None
        except Exception as e:
            self.logger.error(f'PDF OCR parse failed: {e}')
            return None
    
    def _extract_main_body(self, pages_text: List[Dict]) -> str:
        if not pages_text:
            return ''
        
        if len(pages_text) == 1:
            return self._clean_pdf_text(pages_text[0]['text'])
        
        valid_pages = []
        for p in pages_text:
            text = p['text']
            jp_chars = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', text))
            if jp_chars >= 50:
                valid_pages.append(text)
        
        if not valid_pages:
            valid_pages = [p['text'] for p in pages_text]
        
        combined = '\n\n'.join(valid_pages)
        return self._clean_pdf_text(combined)
    
    def _clean_pdf_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'[\r\u0000-\u0008\u000b\u000c\u000e-\u001f]', '', text)
        return text.strip()
    
    def _extract_metadata_from_pdf_text(self, text: str) -> Dict:
        meta = {'title': '', 'author': '', 'school': '', 'date': ''}
        
        title_match = re.search(r'タイトル[：:\s]*([^\n]+)', text)
        if title_match:
            meta['title'] = title_match.group(1).strip()
        else:
            lines = text.split('\n')
            for line in lines[:5]:
                line_clean = re.sub(r'[0-9××]+', '', line).strip()
                if line_clean and len(line_clean) >= 2 and len(line_clean) <= 20:
                    has_jp = bool(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', line_clean))
                    if has_jp:
                        meta['title'] = line_clean
                        break
        
        author_match = re.search(r'(作者|氏名|名前|児童名|生徒名)[：:\s]*([^\n]+)', text)
        if author_match:
            meta['author'] = author_match.group(2).strip()
        else:
            author_match2 = re.search(r'(\d+年)([^\n]+)', text)
            if author_match2:
                year_part = author_match2.group(1)
                rest = author_match2.group(2).strip()
                kanji_name = re.search(r'([\u4e00-\u9fff]{2,4})\s*([ぁ-んァ-ヶー]+)', rest)
                if kanji_name:
                    meta['author'] = kanji_name.group(1) + ' ' + kanji_name.group(2)
        
        school_match = re.search(r'(学校|学園|小学校|中学校)[：:\s]*([^\n]+)', text)
        if school_match:
            meta['school'] = school_match.group(2).strip()
        
        date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', text)
        if date_match:
            meta['date'] = date_match.group(0)
        
        return meta
