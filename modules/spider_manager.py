import importlib
import os
import logging
from typing import List, Dict
from modules.spider_base import SpiderBase


class SpiderManager:
    def __init__(self, spiders_dir='spiders'):
        self.spiders_dir = spiders_dir
        self.spiders: Dict[str, SpiderBase] = {}
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
    
    def list_sites(self) -> List[str]:
        return list(self.spiders.keys())
    
    def crawl_site(self, site_name: str, max_count: int = None) -> List[Dict]:
        spider = self.get_spider(site_name)
        if not spider:
            self.logger.error(f'Spider not found: {site_name}')
            return []
        return spider.crawl(max_count=max_count)
    
    def crawl_all(self, max_per_site: int = None) -> Dict[str, List[Dict]]:
        results = {}
        for site_name, spider in self.spiders.items():
            self.logger.info(f'Starting crawl: {site_name}')
            try:
                essays = spider.crawl(max_count=max_per_site)
                results[site_name] = essays
            except Exception as e:
                self.logger.error(f'Crawl failed [{site_name}]: {e}')
                results[site_name] = []
        return results
