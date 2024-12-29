# import asyncio
# import logging
# from datetime import datetime
# from hot_search import BaiduHotSearch
# from search import QuarkResourceSearcher
# import json
# from pathlib import Path

# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     handlers=[
#         logging.FileHandler('collector.log'),
#         logging.StreamHandler()
#     ]
# )

# class ResourceCollector:
#     def __init__(self):
#         self.hot_search = BaiduHotSearch()
#         self.searcher = QuarkResourceSearcher()
#         self.results_dir = Path('results')
#         self.results_dir.mkdir(exist_ok=True)
        
#     async def close(self):
#         await self.hot_search.close()
#         await self.searcher.close()
        
#     def format_for_wechat(self, item, result) -> str:
#         """格式化为适合微信分享的格式"""
#         template = (
#             f"🔥 {item['category']}推荐\n"
#             f"📺 {item['title']}\n"
#             f"🌟 热度: {item['hot_score']}\n"
#             f"🔗 资源链接: {result['link']}\n"
#             f"⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
#             f"♥️ 欢迎关注，每日更新热门资源"
#         )
#         return template
        
#     async def collect_resources(self, test_mode=True):
#         """收集资源的主函数"""
#         try:
#             # 获取热搜
#             hot_items = await self.hot_search.get_hot_searches()
#             if not hot_items:
#                 logging.error("未获取到热搜数据")
#                 return
                
#             # 测试模式只处理第一个项目
#             if test_mode:
#                 hot_items = hot_items[:1]
                
#             results = []
#             for item in hot_items:
#                 try:
#                     logging.info(f"正在处理: {item['title']}")
                    
#                     # 搜索资源
#                     search_results = []
#                     async for result in self.searcher.search_messages_stream(item['title']):
#                         if result:
#                             # 格式化结果
#                             formatted_msg = self.format_for_wechat(item, result)
#                             results.append({
#                                 'item': item,
#                                 'result': result,
#                                 'formatted_message': formatted_msg
#                             })
#                             break  # 每个热搜只取第一个结果
                            
#                 except Exception as e:
#                     logging.error(f"处理{item['title']}时出错: {str(e)}")
#                     continue
                    
#             # 保存结果
#             if results:
#                 timestamp = datetime.now().strftime('%Y%m%d_%H%M')
#                 result_file = self.results_dir / f'results_{timestamp}.json'
#                 with open(result_file, 'w', encoding='utf-8') as f:
#                     json.dump(results, f, ensure_ascii=False, indent=2)
                    
#                 # 生成当日最新结果的快捷方式
#                 latest_file = self.results_dir / 'latest.json'
#                 with open(latest_file, 'w', encoding='utf-8') as f:
#                     json.dump(results, f, ensure_ascii=False, indent=2)
                    
#                 logging.info(f"已保存{len(results)}个资源到{result_file}")
                
#                 # 打印格式化消息
#                 for result in results:
#                     print("\n" + "="*50)
#                     print(result['formatted_message'])
#                     print("="*50)
                    
#         except Exception as e:
#             logging.error(f"收集资源时��错: {str(e)}")
#             raise

# async def main():
#     collector = ResourceCollector()
#     try:
#         # 测试模式
#         await collector.collect_resources(test_mode=True)
#     finally:
#         await collector.close()

# if __name__ == "__main__":
#     asyncio.run(main()) 