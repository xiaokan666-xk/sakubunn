from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os
import logging


class WordExporter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def export_single(self, essay, save_path):
        try:
            doc = Document()
            
            style = doc.styles['Normal']
            font = style.font
            font.name = 'MS Gothic'
            font.size = Pt(12)
            
            title = doc.add_heading(essay['title'], level=1)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            info_paragraph = doc.add_paragraph()
            info_paragraph.add_run(f'来源: {essay["source_name"]}\n').bold = True
            info_paragraph.add_run(f'URL: {essay["source_url"]}\n')
            info_paragraph.add_run(f'字数: {essay["word_count"]}')
            
            doc.add_paragraph()
            
            content_paragraph = doc.add_paragraph(essay['content'])
            content_paragraph.paragraph_format.line_spacing = 1.5
            
            doc.save(save_path)
            self.logger.info(f'Exported: {save_path}')
            return True
        except Exception as e:
            self.logger.error(f'Export error: {save_path} - {str(e)}')
            return False

    def export_batch(self, essays, save_path):
        try:
            doc = Document()
            
            style = doc.styles['Normal']
            font = style.font
            font.name = 'MS Gothic'
            font.size = Pt(12)
            
            for i, essay in enumerate(essays, 1):
                title = doc.add_heading(f'{i}. {essay["title"]}', level=1)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                info_paragraph = doc.add_paragraph()
                info_paragraph.add_run(f'来源: {essay["source_name"]}\n').bold = True
                info_paragraph.add_run(f'URL: {essay["source_url"]}\n')
                info_paragraph.add_run(f'字数: {essay["word_count"]}')
                
                doc.add_paragraph()
                
                content_paragraph = doc.add_paragraph(essay['content'])
                content_paragraph.paragraph_format.line_spacing = 1.5
                
                if i < len(essays):
                    doc.add_page_break()
            
            doc.save(save_path)
            self.logger.info(f'Batch exported {len(essays)} essays: {save_path}')
            return True
        except Exception as e:
            self.logger.error(f'Batch export error: {save_path} - {str(e)}')
            return False
