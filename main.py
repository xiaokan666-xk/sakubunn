import os
import sys
import webbrowser
import threading
import logging
from flask import Flask, render_template, request, jsonify, send_file
from config import DB_PATH, LOG_FILE
from modules.cache import CacheManager
from modules.crawler import Crawler
from modules.html_parser import HTMLParser
from modules.pdf_parser import PDFParser
from modules.ocr_engine import OCREngine
from modules.formatter import Formatter
from modules.exporter import WordExporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

cache_manager = CacheManager()
crawler = Crawler()
html_parser = HTMLParser()
pdf_parser = PDFParser()
ocr_engine = OCREngine()
formatter = Formatter()
exporter = WordExporter()


@app.route('/')
def index():
    stats = cache_manager.get_stats()
    return render_template('index.html', stats=stats)


@app.route('/api/essays', methods=['GET'])
def get_essays():
    keyword = request.args.get('keyword', '')
    source = request.args.get('source', '')
    essays = cache_manager.search_essays(keyword=keyword, source=source)
    
    result = []
    for essay in essays:
        result.append({
            'id': essay[0],
            'title': essay[1],
            'content': essay[2],
            'source_url': essay[3],
            'source_name': essay[4],
            'category': essay[5],
            'grade': essay[6],
            'word_count': essay[7],
            'crawl_time': essay[8]
        })
    
    return jsonify(result)


@app.route('/api/essay/<int:essay_id>', methods=['GET'])
def get_essay(essay_id):
    essay = cache_manager.get_essay_by_id(essay_id)
    if essay:
        return jsonify({
            'id': essay[0],
            'title': essay[1],
            'content': essay[2],
            'source_url': essay[3],
            'source_name': essay[4],
            'category': essay[5],
            'grade': essay[6],
            'word_count': essay[7],
            'crawl_time': essay[8]
        })
    return jsonify({'error': 'Essay not found'}), 404


@app.route('/api/sources', methods=['GET'])
def get_sources():
    stats = cache_manager.get_stats()
    sources = list(stats.get('by_source', {}).keys())
    return jsonify(sources)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = cache_manager.get_stats()
    return jsonify(stats)


@app.route('/api/export/<int:essay_id>', methods=['GET'])
def export_single(essay_id):
    essay = cache_manager.get_essay_by_id(essay_id)
    if not essay:
        return jsonify({'error': 'Essay not found'}), 404
    
    essay_data = {
        'title': essay[1],
        'content': essay[2],
        'source_url': essay[3],
        'source_name': essay[4],
        'word_count': essay[7]
    }
    
    filename = f'{essay[1][:20]}.docx'.replace('/', '_').replace('\\', '_')
    save_path = os.path.join(os.path.dirname(DB_PATH), filename)
    
    if exporter.export_single(essay_data, save_path):
        return send_file(save_path, as_attachment=True)
    return jsonify({'error': 'Export failed'}), 500


@app.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json
    source_name = data.get('source_name', '')
    
    return jsonify({'status': 'success', 'message': f'Started crawling {source_name}'})


def open_browser():
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
