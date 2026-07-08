import pytesseract
from PIL import Image
import logging


class OCREngine:
    def __init__(self, lang='jpn'):
        self.lang = lang
        self.logger = logging.getLogger(__name__)
        self._check_tesseract()

    def _check_tesseract(self):
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            self.logger.warning(f'Tesseract not found: {str(e)}')

    def recognize(self, image_path):
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang=self.lang)
            return text.strip()
        except Exception as e:
            self.logger.error(f'OCR error: {image_path} - {str(e)}')
            return None

    def recognize_from_bytes(self, image_bytes):
        try:
            img = Image.open(image_bytes)
            text = pytesseract.image_to_string(img, lang=self.lang)
            return text.strip()
        except Exception as e:
            self.logger.error(f'OCR error from bytes: {str(e)}')
            return None
