import aiohttp
import logging
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict

class BaiduHotSearch:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        await self.session.close()
        
    async def get_hot_searches(self) -> List[Dict[str, str]]:
        """获取百度热搜榜前10的影视作品"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # 获取电影热搜
            movie_url = 'https://top.baidu.com/board?tab=movie'
            movie_items = await self._fetch_items(movie_url, headers, category='电影')
            
            # 获取电视剧热搜
            tv_url = 'https://top.baidu.com/board?tab=teleplay'
            tv_items = await self._fetch_items(tv_url, headers, category='电视剧')
            
            # 获取小说热搜
            novel_url = 'https://top.baidu.com/board?tab=novel'
            novel_items = await self._fetch_items(novel_url, headers, category='小说')
            
            # 合并结果并只取前10
            all_items = movie_items + tv_items + novel_items
            all_items.sort(key=lambda x: int(x['hot_score'].replace(',', '')), reverse=True)
            
            return all_items[:10]
            
        except Exception as e:
            logging.error(f"获取百度热搜失败: {str(e)}")
            return []
            
    async def _fetch_items(self, url: str, headers: dict, category: str) -> List[Dict[str, str]]:
        """获取特定分类的热搜项目"""
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return []
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                items = []
                # 根据实际HTML结构解析热搜项目
                for item in soup.select('.category-wrap_iQLoo'):
                    title = item.select_one('.c-single-text-ellipsis').text.strip()
                    hot_score = item.select_one('.hot-index_1Bl1a').text.strip()
                    items.append({
                        'title': title,
                        'hot_score': hot_score,
                        'category': category
                    })
                
                return items[:10]  # 每个分类取前10
                
        except Exception as e:
            logging.error(f"获取{category}热搜失败: {str(e)}")
            return [] 