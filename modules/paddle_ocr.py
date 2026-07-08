import logging
import os
from typing import List, Dict, Optional


class PaddleOCREngine:
    def __init__(self, lang='japan', use_angle_cls=True):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.logger = logging.getLogger(__name__)
        self._ocr = None
        self._available = None
    
    def _get_ocr(self):
        if self._ocr is not None:
            return self._ocr
        
        if self._available is False:
            return None
        
        try:
            from paddleocr import PaddleOCR
            self.logger.info('Initializing PaddleOCR (first use may download models)...')
            self._ocr = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                show_log=False
            )
            self._available = True
            return self._ocr
        except ImportError:
            self.logger.warning('PaddleOCR not installed. Run: pip install paddleocr paddlepaddle')
            self._available = False
            return None
        except Exception as e:
            self.logger.error(f'PaddleOCR init failed: {e}')
            self._available = False
            return None
    
    def is_available(self) -> bool:
        return self._get_ocr() is not None
    
    def recognize(self, image_path: str) -> List[Dict]:
        ocr = self._get_ocr()
        if not ocr:
            return []
        
        try:
            result = ocr.ocr(image_path, cls=self.use_angle_cls)
            items = []
            if result and result[0]:
                for line in result[0]:
                    box = line[0]
                    text = line[1][0]
                    confidence = line[1][1]
                    items.append({
                        'box': box,
                        'text': text,
                        'confidence': confidence
                    })
            return items
        except Exception as e:
            self.logger.error(f'OCR recognition failed: {image_path} - {e}')
            return []
    
    def recognize_to_text(self, image_path: str) -> str:
        items = self.recognize(image_path)
        if not items:
            return ''
        
        sorted_items = self._sort_reading_order(items)
        return '\n'.join([item['text'] for item in sorted_items])
    
    def recognize_bytes(self, image_bytes) -> List[Dict]:
        ocr = self._get_ocr()
        if not ocr:
            return []
        
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name
            try:
                return self.recognize(tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f'OCR from bytes failed: {e}')
            return []
    
    def _sort_reading_order(self, items: List[Dict]) -> List[Dict]:
        if not items:
            return items
        
        boxes = [item['box'] for item in items]
        heights = [self._box_height(b) for b in boxes]
        avg_height = sum(heights) / len(heights) if heights else 0
        
        aspect_ratios = [self._box_aspect(b) for b in boxes]
        is_vertical = avg_height > 0 and sum(1 for ar in aspect_ratios if ar < 1) > sum(1 for ar in aspect_ratios if ar >= 1)
        
        if is_vertical:
            return self._sort_vertical(items)
        else:
            return self._sort_horizontal(items)
    
    def _box_height(self, box) -> float:
        ys = [p[1] for p in box]
        return max(ys) - min(ys)
    
    def _box_width(self, box) -> float:
        xs = [p[0] for p in box]
        return max(xs) - min(xs)
    
    def _box_aspect(self, box) -> float:
        w = self._box_width(box)
        h = self._box_height(box)
        return w / h if h else 0
    
    def _box_center(self, box) -> tuple:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    
    def _sort_horizontal(self, items: List[Dict]) -> List[Dict]:
        sorted_items = sorted(items, key=lambda x: (self._box_center(x['box'])[1], self._box_center(x['box'])[0]))
        return sorted_items
    
    def _sort_vertical(self, items: List[Dict]) -> List[Dict]:
        sorted_items = sorted(items, key=lambda x: (self._box_center(x['box'])[0], -self._box_center(x['box'])[1]))
        return sorted_items
