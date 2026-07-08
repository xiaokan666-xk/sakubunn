import os
import json
from datetime import datetime
from typing import Dict, List
from config import DATA_DIR


class CrawlReport:
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = datetime.now()
        self.results = {}

    def add_site_result(self, site_name: str, site_url: str, essays: List[Dict], failures: List[Dict], parse_types: List[str] = None):
        success = len(essays) > 0 or len(failures) == 0
        self.results[site_name] = {
            'site_name': site_name,
            'site_url': site_url,
            'success': success,
            'essay_count': len(essays),
            'failures': failures,
            'parse_types': parse_types or self._infer_parse_types(essays, failures),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _infer_parse_types(self, essays: List[Dict], failures: List[Dict]) -> List[str]:
        types = []
        for essay in essays:
            source = essay.get('source', '')
            if source and '.pdf' in source.lower():
                if essay.get('body') and len(essay.get('body', '')) > 100:
                    types.append('PDF解析成功')
                else:
                    types.append('PDF OCR完成')
            else:
                types.append('HTML解析成功')
        for f in failures:
            error_type = f.get('error_type', '')
            if 'PDF' in error_type:
                types.append('PDF解析失败')
            elif 'OCR' in error_type:
                types.append('OCR失败')
        return list(set(types))

    def end(self):
        self.end_time = datetime.now()

    def generate_text_report(self) -> str:
        lines = []
        lines.append(f"抓取报告 - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 40)
        lines.append("")

        for site_name, result in self.results.items():
            status_icon = "✔" if result['success'] else "✘"
            lines.append(f"{status_icon} {site_name}")

            if result['success']:
                lines.append(f"新增 {result['essay_count']} 篇作文")
                for parse_type in result['parse_types']:
                    lines.append(parse_type)
            else:
                lines.append("抓取失败")
                for failure in result['failures']:
                    error_msg = failure.get('error_msg', '未知错误')
                    lines.append(error_msg)

            lines.append("—" * 20)
            lines.append("")

        total_essays = sum(r['essay_count'] for r in self.results.values())
        success_sites = sum(1 for r in self.results.values() if r['success'])
        failed_sites = sum(1 for r in self.results.values() if not r['success'])

        lines.append(f"总计：{success_sites} 个网站成功，{failed_sites} 个网站失败")
        lines.append(f"新增作文：{total_essays} 篇")
        lines.append(f"耗时：{self._format_duration()}")

        return '\n'.join(lines)

    def generate_json_report(self) -> Dict:
        return {
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else '',
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else '',
            'duration_seconds': self._get_duration_seconds(),
            'total_essays': sum(r['essay_count'] for r in self.results.values()),
            'success_count': sum(1 for r in self.results.values() if r['success']),
            'failed_count': sum(1 for r in self.results.values() if not r['success']),
            'sites': self.results
        }

    def save_report(self, filename: str = None) -> str:
        if not filename:
            filename = f"crawl_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"

        report_path = os.path.join(DATA_DIR, 'reports')
        os.makedirs(report_path, exist_ok=True)

        filepath = os.path.join(report_path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.generate_json_report(), f, ensure_ascii=False, indent=2)

        return filepath

    def _get_duration_seconds(self) -> int:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return 0

    def _format_duration(self) -> str:
        seconds = self._get_duration_seconds()
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}分{secs}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}小时{minutes}分"


class CrawlReportManager:
    def __init__(self):
        self.reports_dir = os.path.join(DATA_DIR, 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)

    def get_latest_reports(self, limit: int = 10) -> List[Dict]:
        reports = []
        if not os.path.isdir(self.reports_dir):
            return reports

        files = sorted(
            [f for f in os.listdir(self.reports_dir) if f.endswith('.json')],
            reverse=True
        )[:limit]

        for filename in files:
            filepath = os.path.join(self.reports_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    report['filename'] = filename
                    reports.append(report)
            except Exception:
                continue

        return reports

    def get_report_by_filename(self, filename: str) -> Dict:
        filepath = os.path.join(self.reports_dir, filename)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None