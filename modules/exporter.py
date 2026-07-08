from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os
import logging


class WordExporter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def export_single(self, essay, save_path):
        try:
            doc = Document()
            self._set_default_style(doc)
            
            # Title
            title = doc.add_heading(essay['title'], level=1)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Meta info
            info = doc.add_paragraph()
            info.alignment = WD_ALIGN_PARAGRAPH.CENTER
            info.add_run(f'来源：{essay["source_name"]}\n').bold = True
            info.add_run(f'URL：{essay["source_url"]}\n')
            info.add_run(f'字数：{essay["word_count"]} 字')
            
            doc.add_paragraph()
            
            # Content
            content = doc.add_paragraph(essay['content'])
            content.paragraph_format.line_spacing = 1.8
            
            doc.save(save_path)
            self.logger.info(f'Exported: {save_path}')
            return True
        except Exception as e:
            self.logger.error(f'Export error: {save_path} - {str(e)}')
            return False

    def export_batch(self, essays, save_path):
        try:
            doc = Document()
            self._set_default_style(doc)
            
            for i, essay in enumerate(essays, 1):
                # Title
                title = doc.add_heading(f'{i}. {essay["title"]}', level=1)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Meta
                info = doc.add_paragraph()
                info.alignment = WD_ALIGN_PARAGRAPH.CENTER
                info.add_run(f'来源：{essay["source_name"]}\n').bold = True
                info.add_run(f'URL：{essay["source_url"]}\n')
                info.add_run(f'字数：{essay["word_count"]} 字')
                
                doc.add_paragraph()
                
                # Content
                content = doc.add_paragraph(essay['content'])
                content.paragraph_format.line_spacing = 1.8
                
                if i < len(essays):
                    doc.add_page_break()
            
            doc.save(save_path)
            self.logger.info(f'Batch exported {len(essays)} essays: {save_path}')
            return True
        except Exception as e:
            self.logger.error(f'Batch export error: {save_path} - {str(e)}')
            return False
    
    def _set_default_style(self, doc):
        style = doc.styles['Normal']
        font = style.font
        font.name = 'MS Gothic'
        font.size = Pt(12)
        font.color.rgb = RGBColor(0x3A, 0x2F, 0x2F)
