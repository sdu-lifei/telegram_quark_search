import asyncio
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any

from src.config import RESULTS_CONFIG, QUARK_CONFIG, WECHAT_CONFIG
from src.baidu.hot_search import BaiduHotSearch
from src.telegram.searcher import TelegramResourceSearcher
from src.wechat.sender import send_results_to_wechat

class ResourceCollector:
    """资源收集器类"""
    
    def __init__(self):
        """初始化资源收集器"""
        if not QUARK_CONFIG['COOKIE']:
            raise ValueError("请在.env文件中设置QUARK_COOKIE")
        self.hot_search = BaiduHotSearch()
        self.searcher = TelegramResourceSearcher(cookie=QUARK_CONFIG['COOKIE'])
        self.results_dir = RESULTS_CONFIG['DIR']
        self.results_dir.mkdir(exist_ok=True)
        
    async def close(self):
        """关闭连接"""
        await self.hot_search.close()
        await self.searcher.close()
        
    async def init(self):
        """初始化资源收集器"""
        try:
            # 初始化搜索器
            if not await self.searcher.init():
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"初始化失败: {str(e)}")
            return False
        
    def format_for_wechat(self, item: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """格式化为适合微信分享的格式"""
        template = (
            f" 🚀🚀 {item['title']}\n"
            f"🔥 热度：{item.get('hot_score', 'N/A')}\n"
        )

        template += f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"

        return template.strip()
        
    async def collect_resources(self, test_mode: bool = False, debug: bool = False) -> List[Dict[str, Any]]:
        """收集资源"""
        results = []

        # 获取热搜
        hot_items = await self.hot_search.get_hot_searches()
        if not hot_items:
            logging.error("获取热搜失败")
            return results

        if debug:
            print(f"获取到 {len(hot_items)} 个热搜项目")

        # 处理每个热搜项目
        for item in hot_items:
            try:
                if debug:
                    print(f"\n处理热搜: {item['title']}")

                # 搜索并保存资源
                search_results = await self.searcher.search_and_save(item["title"])
                if not search_results:
                    if debug:
                        print("未找到相关资源")
                    continue

                # 格式化结果
                formatted_text = self.format_for_wechat(item, search_results)
                results.append({
                    "title": item["title"],
                    "text": formatted_text,
                    "rank": item.get('hot_score', 'N/A'),
                    "search_results": search_results
                })

                if test_mode:
                    break

            except Exception as e:
                logging.error(f"处理热搜项目时出错: {str(e)}", exc_info=True)
                if debug:
                    print(f"处理出错: {str(e)}")
                continue

        # 保存结果到文件
        if results:
            self._save_results(results)
            
            # 发送到微信群
            if WECHAT_CONFIG['ENABLED'] and WECHAT_CONFIG['TARGET_GROUPS']:
                if send_results_to_wechat(results, WECHAT_CONFIG['TARGET_GROUPS']):
                    logging.info("成功发送到微信群")
                else:
                    logging.error("发送到微信群失败")

        return results
            
    def _save_results(self, results: List[Dict[str, Any]]):
        """保存结果到文件"""
        try:
            # 保存带时间戳的结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            result_file = self.results_dir / f'results_{timestamp}.json'
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            # 更新最新结果文件
            with open(RESULTS_CONFIG['LATEST_FILE'], 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            logging.info(f"已保存{len(results)}个资源到{result_file}")
            
        except Exception as e:
            logging.error(f"保存结果时出错: {str(e)}")
            
    def print_results(self, results: List[Dict[str, Any]]):
        """打印格式化的结果"""
        for result in results:
            print("\n" + "="*50)
            print(result['text'])
            print(result['search_results'][0]['text'])
            print("\n")
            print("🔗链接: " + result['search_results'][0]['share_url'])
            print("="*50)