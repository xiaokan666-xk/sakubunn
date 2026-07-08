import os
import sys
import webbrowser
import threading
import logging
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from config import DB_PATH, LOG_FILE
from modules.cache import CacheManager
from modules.exporter import WordExporter
from modules.spider_manager import SpiderManager
from modules.crawl_report import CrawlReport, CrawlReportManager

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
report_manager = CrawlReportManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/essays', methods=['GET'])
def get_essays():
    keyword = request.args.get('keyword', '')
    source = request.args.get('source', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    relative = request.args.get('relative', '')

    if relative:
        if relative == 'week':
            essays = cache_manager.get_essays_by_relative_time(days=7)
        elif relative == 'month':
            essays = cache_manager.get_essays_by_relative_time(months=1)
        elif relative == 'half_year':
            essays = cache_manager.get_essays_by_relative_time(months=6)
        elif relative == 'year':
            essays = cache_manager.get_essays_by_relative_time(months=12)
        else:
            essays = cache_manager.get_all_essays()
    else:
        essays = cache_manager.search_essays(
            keyword=keyword,
            source=source,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None
        )
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
    updates = cache_manager.get_all_site_updates()
    for site in sites:
        info = updates.get(site['name'], {})
        site['last_update'] = info.get('last_update', '')
        site['essay_count'] = info.get('essay_count', 0)
    return jsonify(sites)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = cache_manager.get_stats()
    site_updates = cache_manager.get_all_site_updates()
    stats['site_updates'] = site_updates
    return jsonify(stats)


@app.route('/api/export/<int:essay_id>', methods=['GET'])
def export_single(essay_id):
    essay = cache_manager.get_essay_by_id(essay_id)
    if not essay:
        return jsonify({'error': 'Essay not found'}), 404

    essay_data = {
        'title': essay['title'],
        'author': essay['author'],
        'school': essay['school'],
        'body': essay['body'],
        'source': essay['source'],
        'date': essay['date'],
        'site': essay['site']
    }

    filename = f"{essay['title'][:30]} {essay['site']}.docx".replace('/', '_').replace('\\', '_')
    save_path = os.path.join(os.path.dirname(DB_PATH), filename)

    if exporter.export_single(essay_data, save_path):
        return send_file(save_path, as_attachment=True)
    return jsonify({'error': 'Export failed'}), 500


@app.route('/api/export_batch', methods=['GET'])
def export_batch():
    ids_param = request.args.get('ids', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    essays = []
    if ids_param:
        try:
            ids = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
            essays = cache_manager.get_essays_by_ids(ids)
        except ValueError:
            return jsonify({'error': 'Invalid IDs'}), 400
    elif date_from and date_to:
        essays = cache_manager.get_essays_by_date_range(date_from, date_to)
    else:
        return jsonify({'error': 'No IDs or date range provided'}), 400

    if not essays:
        return jsonify({'error': 'No essays found'}), 404

    essay_data_list = []
    for essay in essays:
        essay_data_list.append({
            'title': essay['title'],
            'author': essay['author'],
            'school': essay['school'],
            'body': essay['body'],
            'source': essay['source'],
            'date': essay['date'],
            'site': essay['site']
        })

    if date_from and date_to:
        df = date_from.replace('-', '.').split(' ')[0]
        dt = date_to.replace('-', '.').split(' ')[0]
        filename = f"作文大赏{df}-{dt}.docx"
    else:
        filename = f"batch_export_{len(essay_data_list)}_essays.docx"

    save_path = os.path.join(os.path.dirname(DB_PATH), filename)

    if exporter.export_batch(essay_data_list, save_path, date_from=date_from, date_to=date_to):
        return send_file(save_path, as_attachment=True)
    return jsonify({'error': 'Export failed'}), 500


@app.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json or {}
    site_name = data.get('site_name', '')
    full_mode = data.get('full_mode', False)

    def essay_exists_fn(url):
        return cache_manager.essay_exists_by_url(url)

    report = CrawlReport()
    report.start()

    if site_name:
        spider = spider_manager.get_spider(site_name)
        result = spider_manager.crawl_site(site_name, essay_exists_fn=essay_exists_fn, full_mode=full_mode, resource_cache=cache_manager)
        if result['success']:
            inserted = 0
            for essay in result['essays']:
                if cache_manager.insert_essay(essay):
                    inserted += 1
            cache_manager.update_site_crawl_time(site_name, spider.site_url)
        report.add_site_result(site_name, spider.site_url if spider else '', result['essays'], result['failures'])
        report.end()
        report.save_report()
        return jsonify({
            'success': result['success'],
            'count': len(result['essays']),
            'failures': result['failures'],
            'report': report.generate_text_report()
        })
    else:
        results = spider_manager.crawl_all(essay_exists_fn=essay_exists_fn, full_mode=full_mode, resource_cache=cache_manager)
        total_count = 0
        for site_name, result in results.items():
            spider = spider_manager.get_spider(site_name)
            inserted = 0
            for essay in result['essays']:
                if cache_manager.insert_essay(essay):
                    inserted += 1
            total_count += inserted
            if result['essays']:
                cache_manager.update_site_crawl_time(site_name, spider.site_url)
            report.add_site_result(site_name, spider.site_url, result['essays'], result['failures'])
        report.end()
        report.save_report()
        return jsonify({
            'success': total_count > 0,
            'count': total_count,
            'report': report.generate_text_report()
        })


@app.route('/api/reports', methods=['GET'])
def get_reports():
    limit = request.args.get('limit', 10, type=int)
    reports = report_manager.get_latest_reports(limit)
    return jsonify(reports)


@app.route('/api/report/<filename>', methods=['GET'])
def get_report(filename):
    report = report_manager.get_report_by_filename(filename)
    if report:
        return jsonify(report)
    return jsonify({'error': 'Report not found'}), 404


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