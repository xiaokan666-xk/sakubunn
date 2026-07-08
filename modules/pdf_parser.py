import pdfplumber
import logging


class PDFParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(self, file_path):
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n\n'
                return text.strip()
        except Exception as e:
            self.logger.error(f'PDF parse error: {file_path} - {str(e)}')
            return None

    def get_page_count(self, file_path):
        try:
            with pdfplumber.open(file_path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            self.logger.error(f'PDF page count error: {file_path} - {str(e)}')
            return 0
