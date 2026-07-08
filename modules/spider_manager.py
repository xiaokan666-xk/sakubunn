import importlib
import os
import logging
from typing import List, Dict
from modules.spider_base import SpiderBase
from modules.error_tracker import ErrorTracker


class SpiderManager:
    def __init__(self, spiders_dir='spiders'):
        self.spiders_dir = spiders_dir
        self.spiders: Dict[str, SpiderBase] = {}
        self.error_tracker = ErrorTracker()
        self.logger = logging.getLogger(__name__)
        self._load_spiders()

    def _load_spiders(self):
        if not os.path.isdir(self.spiders_dir):
            self.logger.warning(f'Spiders directory not found: {self.spiders_dir}')
            return

        for filename in os.listdir(self.spiders_dir):
            if filename.startswith('_') or not filename.endswith('.py'):
                continue
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f'{self.spiders_dir}.{module_name}')
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, SpiderBase) and
                        attr is not SpiderBase and
                        hasattr(attr, 'site_name') and attr.site_name):
                        spider = attr()
                        self.spiders[spider.site_name] = spider
                        self.logger.info(f'Loaded spider: {spider.site_name}')
            except Exception as e:
                self.logger.error(f'Failed to load spider {module_name}: {e}')

    def get_spider(self, site_name: str) -> SpiderBase:
        return self.spiders.get(site_name)

    def list_sites(self) -> List[Dict]:
        return [
            {'name': spider.site_name, 'url': spider.site_url}
            for spider in self.spiders.values()
        ]

    def get_failed_sites(self) -> List[Dict]:
        failed = []
        for site_name, spider in self.spiders.items():
            errors = self.error_tracker.get_errors(site_name)
            if errors:
                latest = errors[-1]
                failed.append({
                    'site_name': site_name,
                    'site_url': spider.site_url,
                    'error_type': latest.get('error_type', ''),
                    'error_msg': latest.get('error_msg', ''),
                    'time': latest.get('time', ''),
                    'is_site_update_suspicion': latest.get('is_site_update_suspicion', False),
                    'error_count': len(errors)
                })
        return failed

    def get_all_site_status(self) -> List[Dict]:
        status = []
        for site_name, spider in self.spiders.items():
            errors = self.error_tracker.get_errors(site_name)
            latest_error = errors[-1] if errors else None
            status.append({
                'site_name': site_name,
                'site_url': spider.site_url,
                'has_error': bool(errors),
                'error_count': len(errors),
                'latest_error': latest_error
            })
        return status

    def crawl_site(self, site_name: str, max_count: int = None, essay_exists_fn=None, full_mode: bool = False, resource_cache=None) -> Dict:
        spider = self.get_spider(site_name)
        if not spider:
            self.logger.error(f'Spider not found: {site_name}')
            return {
                'success': False,
                'essays': [],
                'failures': [{
                    'site_name': site_name,
                    'site_url': '',
                    'url': '',
                    'error_type': 'SPIDER_NOT_FOUND',
                    'error_msg': f'未找到该网站对应的Spider: {site_name}'
                }]
            }

        try:
            if resource_cache:
                spider.set_resource_cache(resource_cache)
            essays = spider.crawl(max_count=max_count, essay_exists_fn=essay_exists_fn, full_mode=full_mode)
            failures = spider.get_failures()
            return {
                'success': len(essays) > 0 or len(failures) == 0,
                'essays': essays,
                'failures': failures
            }
        except Exception as e:
            self.logger.error(f'Crawl failed [{site_name}]: {e}')
            return {
                'success': False,
                'essays': [],
                'failures': [{
                    'site_name': site_name,
                    'site_url': spider.site_url,
                    'url': '',
                    'error_type': 'CRAWL_EXCEPTION',
                    'error_msg': str(e)
                }]
            }

    def crawl_all(self, max_per_site: int = None, essay_exists_fn=None, full_mode: bool = False, resource_cache=None) -> Dict:
        results = {}
        for site_name, spider in self.spiders.items():
            self.logger.info(f'Starting crawl: {site_name}')
            result = self.crawl_site(site_name, max_count=max_per_site, essay_exists_fn=essay_exists_fn, full_mode=full_mode, resource_cache=resource_cache)
            results[site_name] = result
        return results
