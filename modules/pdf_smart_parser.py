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
        
        author_match = re.search(r'(作者|氏名|名前|児童名|生徒名)[：:\s]*([^\n]+)', text)
        if author_match:
            meta['author'] = author_match.group(2).strip()
        
        school_match = re.search(r'(学校|学園|小学校|中学校)[：:\s]*([^\n]+)', text)
        if school_match:
            meta['school'] = school_match.group(2).strip()
        
        date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', text)
        if date_match:
            meta['date'] = date_match.group(0)
        
        return meta
