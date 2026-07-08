import os
import sys
import webbrowser
import threading
import logging
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from config import DB_PATH, LOG_FILE
from modules.cache import CacheManager
from modules.exporter import WordExporter
from modules.spider_manager import SpiderManager

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
exporter = WordExporter()
spider_manager = SpiderManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/essays', methods=['GET'])
def get_essays():
    keyword = request.args.get('keyword', '')
    source = request.args.get('source', '')
    essays = cache_manager.search_essays(keyword=keyword, source=source)
    return jsonify(essays)


@app.route('/api/essay/<int:essay_id>', methods=['GET'])
def get_essay(essay_id):
    essay = cache_manager.get_essay_by_id(essay_id)
    if essay:
        return jsonify(essay)
    return jsonify({'error': 'Essay not found'}), 404


@app.route('/api/sites', methods=['GET'])
def get_sites():
    sites = spider_manager.list_sites()
    return jsonify(sites)


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
        'title': essay['title'],
        'content': essay['body'],
        'source_url': essay['source'],
        'source_name': essay['site'],
        'word_count': len(essay['body'])
    }

    filename = f"{essay['title'][:30]}.docx".replace('/', '_').replace('\\', '_')
    save_path = os.path.join(os.path.dirname(DB_PATH), filename)

    if exporter.export_single(essay_data, save_path):
        return send_file(save_path, as_attachment=True)
    return jsonify({'error': 'Export failed'}), 500


@app.route('/api/export_batch', methods=['GET'])
def export_batch():
    ids_param = request.args.get('ids', '')
    if not ids_param:
        return jsonify({'error': 'No IDs provided'}), 400

    try:
        ids = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
    except ValueError:
        return jsonify({'error': 'Invalid IDs'}), 400

    essays = cache_manager.get_essays_by_ids(ids)
    if not essays:
        return jsonify({'error': 'No essays found'}), 404

    essay_data_list = []
    for essay in essays:
        essay_data_list.append({
            'title': essay['title'],
            'content': essay['body'],
            'source_url': essay['source'],
            'source_name': essay['site'],
            'word_count': len(essay['body'])
        })

    filename = f"batch_export_{len(essay_data_list)}_essays.docx"
    save_path = os.path.join(os.path.dirname(DB_PATH), filename)

    if exporter.export_batch(essay_data_list, save_path):
        return send_file(save_path, as_attachment=True)
    return jsonify({'error': 'Export failed'}), 500


@app.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json or {}
    site_name = data.get('site_name', '')

    if site_name:
        result = spider_manager.crawl_site(site_name)
        if result['success']:
            for essay in result['essays']:
                cache_manager.insert_essay(essay)
        return jsonify({
            'success': result['success'],
            'count': len(result['essays']),
            'failures': result['failures']
        })
    else:
        results = spider_manager.crawl_all()
        total_count = 0
        all_failures = []
        for site_name, result in results.items():
            for essay in result['essays']:
                cache_manager.insert_essay(essay)
            total_count += len(result['essays'])
            all_failures.extend(result['failures'])
        return jsonify({
            'success': total_count > 0,
            'count': total_count,
            'failures': all_failures
        })


@app.route('/api/failed_sites', methods=['GET'])
def get_failed_sites():
    return jsonify(spider_manager.get_failed_sites())


@app.route('/api/site_status', methods=['GET'])
def get_site_status():
    return jsonify(spider_manager.get_all_site_status())


def open_browser():
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
