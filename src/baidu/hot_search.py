import aiohttp
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import asyncio

class BaiduHotSearch:
    """百度热搜获取类"""
    
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    async def close(self):
        """关闭会话"""
        await self.session.close()
        
    async def get_hot_searches(self) -> List[Dict[str, Any]]:
        """获取百度热搜榜前10的影视作品"""
        try:
            tasks = [
                self._fetch_items('https://top.baidu.com/board?tab=movie', '电影'),
                self._fetch_items('https://top.baidu.com/board?tab=teleplay', '电视剧'),
                self._fetch_items('https://top.baidu.com/board?tab=novel', '小说')
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_items = []
            for items in results:
                if isinstance(items, Exception):
                    logging.error(f"获取热搜失败: {str(items)}")
                    continue
                all_items.extend(items)
            
            # 按热度排序
            all_items.sort(key=lambda x: int(x['hot_score'].replace(',', '')), reverse=True)
            
            return all_items[:10]
            
        except Exception as e:
            logging.error(f"获取百度热搜失败: {str(e)}")
            return []
            
    async def _fetch_items(self, url: str, category: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """获取特定分类的热搜项目"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                async with self.session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        logging.error(f"获取{category}热搜失败，状态码: {response.status}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(1)
                            continue
                        return []
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    items = []
                    for item in soup.select('.category-wrap_iQLoo'):
                        try:
                            title_elem = item.select_one('.c-single-text-ellipsis')
                            hot_elem = item.select_one('.hot-index_1Bl1a')
                            
                            if not title_elem or not hot_elem:
                                continue
                                
                            title = title_elem.text.strip()
                            hot_score = hot_elem.text.strip()
                            
                            if title and hot_score:
                                items.append({
                                    'title': title,
                                    'hot_score': hot_score,
                                    'category': category
                                })
                        except Exception as e:
                            logging.warning(f"解析{category}热搜项目时出错: {str(e)}")
                            continue
                    
                    if not items:
                        logging.warning(f"未找到{category}热搜项目")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(1)
                            continue
                            
                    return items[:10]  # 每个分类取前10
                    
            except Exception as e:
                logging.error(f"获取{category}热搜失败: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(1)
                    continue
                return []
                
        return []
