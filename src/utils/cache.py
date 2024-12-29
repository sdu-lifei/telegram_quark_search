import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.config import CACHE_CONFIG

class SearchCache:
    """搜索缓存"""
    
    def __init__(self):
        self.cache_file = Path(CACHE_CONFIG['SEARCH_CACHE_FILE'])
        self.cache = {}  # 初始化为空字典
        self.load()  # 加载缓存
        
    def load(self):
        """加载缓存"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
                self.save()  # 创建空缓存文件
        except json.JSONDecodeError:
            logging.warning("缓存文件损坏，重置缓存")
            self.cache = {}
            self.save()  # 保存空缓存
        except Exception as e:
            logging.error(f"加载缓存失败: {str(e)}")
            self.cache = {}
            self.save()  # 保存空缓存

        # 清理过期缓存
        now = datetime.now()
        self.cache = {
            k: v for k, v in self.cache.items()
            if datetime.fromisoformat(v['timestamp']) > now - timedelta(days=CACHE_CONFIG['EXPIRE_DAYS'])
        }
        self.save()  # 保存清理后的缓存
        
    def save(self):
        """保存缓存数据"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存缓存失败: {str(e)}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存数据"""
        return self.cache.get(key)
    
    def set(self, key: str, results: List[Dict[str, Any]]):
        """设置缓存数据"""
        self.cache[key] = {
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
        self.save()
