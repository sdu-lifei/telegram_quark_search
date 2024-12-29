# from fastapi import FastAPI, Request
# from fastapi.responses import HTMLResponse, StreamingResponse
# from fastapi.templating import Jinja2Templates
# from fastapi.staticfiles import StaticFiles
# import asyncio
# import json
# from search import QuarkResourceSearcher
# import os
# from pathlib import Path
# import logging
# import uvicorn
# import time

# # 修改日志配置
# logging.basicConfig(
#     level=logging.DEBUG,  # 改为 DEBUG 级别
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

# # 修改 uvicorn 日志级别
# uvicorn_logger = logging.getLogger("uvicorn")
# uvicorn_logger.setLevel(logging.DEBUG)
# uvicorn_access_logger = logging.getLogger("uvicorn.access")
# uvicorn_access_logger.setLevel(logging.DEBUG)

# app = FastAPI()

# # 创建templates和static目录
# templates_dir = Path("templates")
# static_dir = Path("static")
# templates_dir.mkdir(exist_ok=True)
# static_dir.mkdir(exist_ok=True)

# # 设置静态文件和模板
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")

# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# async def search_generator(query: str):
#     searcher = QuarkResourceSearcher()
#     try:
#         await searcher.connect_and_login()
        
#         found_any = False
        
#         try:
#             async for result in searcher.search_messages_stream(query, min_similarity=80):
#                 found_any = True
#                 text = result["text"]
#                 similarity = result["similarity"]
                
#                 # 清理文本
#                 text_parts = text.split('\n')
#                 cleaned_parts = []
                
#                 for part in text_parts:
#                     if any(mark in part for mark in [
#                         "📁 大小：", "🏷 标签：", "📢 频道：", "👥 群组：", 
#                         "链接：", "链接:", "https://pan.quark.cn",
#                         "quark://", "#", "@"
#                     ]):
#                         continue
#                     cleaned_parts.append(part.strip())
                
#                 text = '\n'.join(part for part in cleaned_parts if part)
                
#                 try:
#                     save_result = await searcher.quark_api.save_shared_file(result["link"])
#                     if save_result["success"]:
#                         result_json = json.dumps({
#                             "text": text,
#                             "link": save_result["share_url"],
#                             "similarity": similarity
#                         })
#                         yield f"data: {result_json}\n\n"
#                         yield f"data: {json.dumps({'complete': True, 'total': 1})}\n\n"
#                         return
#                 except Exception as e:
#                     logging.error(f"转换链接失败: {str(e)}")
#                     continue
                    
#         except asyncio.TimeoutError as e:
#             yield f"data: {json.dumps({'timeout': True, 'message': str(e)})}\n\n"
#         except Exception as e:
#             logging.error(f"搜索出错: {str(e)}")
#             yield f"data: {json.dumps({'error': True, 'message': str(e)})}\n\n"
            
#     except Exception as e:
#         logging.error(f"搜索出错: {str(e)}")
#         yield f"data: {json.dumps({'error': True, 'message': str(e)})}\n\n"
#     finally:
#         await searcher.close()

# @app.get("/search")
# async def search(query: str):
#     return StreamingResponse(
#         search_generator(query),
#         media_type="text/event-stream"
#     )

# if __name__ == "__main__":
#     uvicorn.run(
#         app, 
#         host="0.0.0.0", 
#         port=8000,
#         log_level="debug",  # 改为 debug
#         access_log=True     # 开启访问日志
#     ) 