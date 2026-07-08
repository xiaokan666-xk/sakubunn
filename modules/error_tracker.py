import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional


class ErrorTracker:
    def __init__(self, error_file=None):
        from config import DATA_DIR
        if error_file is None:
            self.error_file = os.path.join(DATA_DIR, 'crawl_errors.json')
        else:
            self.error_file = error_file
        self.logger = logging.getLogger(__name__)
        self._ensure_file()
    
    def _ensure_file(self):
        if not os.path.exists(self.error_file):
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump({'errors': []}, f, ensure_ascii=False, indent=2)
    
    def record_error(self, site_name: str, site_url: str, url: str, error_type: str, error_msg: str):
        try:
            with open(self.error_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['errors'].append({
                'site_name': site_name,
                'site_url': site_url,
                'url': url,
                'error_type': error_type,
                'error_msg': error_msg,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_site_update_suspicion': self._is_site_update_related(error_type, error_msg)
            })
            
            data['errors'] = data['errors'][-500:]
            
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.error(f'Crawl error recorded [{site_name}]: {error_type} - {error_msg}')
        except Exception as e:
            self.logger.error(f'Failed to record error: {e}')
    
    def _is_site_update_related(self, error_type: str, error_msg: str) -> bool:
        update_indicators = [
            'parse_list_page returned empty',
            'parse_essay_page returned empty',
            'No matching selector',
            'Page structure changed',
            '0 essay links found',
            'body is empty',
            'title is empty',
        ]
        msg_lower = (error_msg or '').lower()
        return any(ind.lower() in msg_lower for ind in update_indicators) or error_type == 'PARSE_EMPTY'
    
    def get_errors(self, site_name: str = None) -> List[Dict]:
        try:
            with open(self.error_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            errors = data.get('errors', [])
            if site_name:
                errors = [e for e in errors if e.get('site_name') == site_name]
            return errors
        except Exception as e:
            self.logger.error(f'Failed to read errors: {e}')
            return []
    
    def get_site_update_suspicions(self) -> List[Dict]:
        try:
            with open(self.error_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [e for e in data.get('errors', []) if e.get('is_site_update_suspicion')]
        except Exception as e:
            self.logger.error(f'Failed to read errors: {e}')
            return []
    
    def get_grouped_errors(self) -> Dict[str, List[Dict]]:
        errors = self.get_errors()
        grouped = {}
        for e in errors:
            site = e.get('site_name', 'Unknown')
            if site not in grouped:
                grouped[site] = []
            grouped[site].append(e)
        return grouped
    
    def clear_errors(self, site_name: str = None):
        try:
            with open(self.error_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if site_name:
                data['errors'] = [e for e in data.get('errors', []) if e.get('site_name') != site_name]
            else:
                data['errors'] = []
            
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f'Failed to clear errors: {e}')
