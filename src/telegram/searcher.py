import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator
from fuzzywuzzy import fuzz
from telethon import TelegramClient
from telethon.tl.types import InputPeerChannel, InputPeerUser, InputPeerChat
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    FloodWaitError,
    ChatAdminRequiredError,
    UserDeactivatedBanError,
)
import re
from datetime import datetime

# from src.config import TELEGRAM_CONFIG, QUARK_CONFIG, V2RAY_CONFIG
from src.config import TELEGRAM_CONFIG, QUARK_CONFIG    
from src.utils.logger import setup_logger
from src.utils.cache import SearchCache
from src.quark.api import QuarkAPI
# from src.utils.v2ray_controller import V2RayController

# 设置日志为DEBUG级别
logger = setup_logger(level=logging.INFO)

class TelegramResourceSearcher:
    """Telegram资源搜索类"""
    
    def __init__(self, cookie: str):
        self.client = None
        self.api_id = TELEGRAM_CONFIG['API_ID']
        self.api_hash = TELEGRAM_CONFIG['API_HASH']
        self.target_groups = TELEGRAM_CONFIG['TARGET_GROUPS']
        self.max_results = TELEGRAM_CONFIG['MAX_RESULTS']
        
        # 初始化夸克网盘 API
        if not cookie:
            raise ValueError("请��.env文件中设置QUARK_COOKIE")
        self.quark_api = QuarkAPI(cookie=cookie)
        self.cache = SearchCache()
        
        # # 初始化V2Ray控制器
        # self.v2ray = V2RayController(
        #     config_path=V2RAY_CONFIG['CONFIG'],
        #     v2ray_path=V2RAY_CONFIG['PATH']
        # ) if V2RAY_CONFIG['ENABLED'] else None
        
    async def init(self):
        """初始化搜索器"""
        try:
            # 如果启用了V2Ray，先启动它
            # if self.v2ray:
            #     if not self.v2ray.start():
            #         logger.error("V2Ray启动失败")
            #         return False
            #     logger.info("V2Ray启动成功")
                
            # 连接 Telegram
            if not self.client:
                self.client = TelegramClient(
                    'quark_searcher',
                    self.api_id,
                    self.api_hash
                )
            
            if not self.client.is_connected():
                await self.client.connect()
                
            if not await self.client.is_user_authorized():
                logging.error("Telegram 未登录，请先登录")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"初始化失败: {str(e)}")
            return False
        
    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.disconnect()
        await self.quark_api.close()
        
        # # 如果V2Ray在运行，停止它
        # if self.v2ray:
        #     self.v2ray.stop()
        #     logger.info("V2Ray已停止")
        
    async def connect_and_login(self, max_retries: int = 3):
        """连接并登录Telegram"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                if not self.client:
                    self.client = TelegramClient(
                        'quark_searcher',
                        self.api_id,
                        self.api_hash
                    )
                
                if not self.client.is_connected():
                    await self.client.connect()
                    
                if not await self.client.is_user_authorized():
                    logging.info("需要登录Telegram账号")
                    await self.client.start()
                    
                # 测试连接
                me = await self.client.get_me()
                if me:
                    logging.info(f"成功连接到Telegram，用户ID: {me.id}")
                    return True
                    
            except SessionPasswordNeededError:
                logging.error("需要2FA密码，请确保已正确设置")
                return False
            except PhoneCodeInvalidError:
                logging.error("验证码无效")
                return False
            except FloodWaitError as e:
                wait_time = e.seconds
                logging.error(f"请求过于频繁，需要等待 {wait_time} 秒")
                if retry_count < max_retries - 1:
                    await asyncio.sleep(min(wait_time, 30))  # 最多等待30秒
                    retry_count += 1
                    continue
                return False
            except Exception as e:
                logging.error(f"连接Telegram时出错: {str(e)}")
                if retry_count < max_retries - 1:
                    await asyncio.sleep(1)
                    retry_count += 1
                    continue
                return False
                
        return False
                
    def calculate_similarity(self, query: str, text: str) -> int:
        """计算文本相似度"""
        # 移除特殊字符和空格进行比较
        query = re.sub(r'[^\w\s]', '', query.lower())
        text = re.sub(r'[^\w\s]', '', text.lower())
        return fuzz.partial_ratio(query, text)
        
    async def _get_entity(self, group_id: str, max_retries: int = 3) -> Any:
        """获取群组实体"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 尝试通过用户名获取
                if group_id.startswith('@'):
                    group_id = group_id[1:]
                return await self.client.get_entity(group_id)
            except ValueError:
                # 如果用户名无效，尝试通过ID获取
                try:
                    group_id_int = int(group_id)
                    return await self.client.get_entity(group_id_int)
                except ValueError:
                    pass
            except FloodWaitError as e:
                wait_time = e.seconds
                logging.error(f"请求过于频繁，需要等待 {wait_time} 秒")
                if retry_count < max_retries - 1:
                    await asyncio.sleep(min(wait_time, 30))
                    retry_count += 1
                    continue
                raise
            except Exception as e:
                logging.error(f"获取群组实体时出错: {str(e)}")
                if retry_count < max_retries - 1:
                    await asyncio.sleep(1)
                    retry_count += 1
                    continue
                raise
                
        raise ValueError(f"无法获取群组: {group_id}")
        
    async def _search_group(
        self, 
        group: str, 
        query: str, 
        min_similarity: int,
        debug: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """搜索单个群组的消息"""
        try:
            entity = await self._get_entity(group)
            group_title = getattr(entity, 'title', group)
            logging.info(f"开始搜索群组: {group_title}")
            if debug:
                print(f"\n开始搜索群组: {group_title}")
            
            # 正则表达式匹配夸克网盘链接
            quark_pattern = r'https?://pan\.quark\.cn/[^\s<>"\']+|quark://[^\s<>"\']+'
            
            message_count = 0
            found_count = 0
            max_results = self.max_results
            
            # 按时间倒序搜索所有消息
            async for message in self.client.iter_messages(
                entity,
                reverse=False,  # False 表示从新到旧
                wait_time=1  # 添加等待时间避免请求过快
            ):
                if not message or not message.text:
                    continue
                    
                message_count += 1
                if debug and message_count % 20 == 0:
                    print(f"已检查 {message_count} 条消息...")
                
                # 计算相似度
                similarity = self.calculate_similarity(query, message.text)
                if similarity < min_similarity:
                    continue
                    
                # 查找夸克网盘链接
                quark_links = re.findall(quark_pattern, message.text)
                if not quark_links:
                    continue
                    
                # 处理每个夸克链接
                for link in quark_links:
                    if found_count >= max_results:
                        log_msg = f"已找到 {max_results} 个结果，停止搜索"
                        logging.info(log_msg)
                        if debug:
                            print(f"\n{log_msg}")
                        return
                        
                    # 检查缓存
                    cache_key = f"{query}:{link}"
                    cached_result = self.cache.get(cache_key)
                    if cached_result:
                        found_count += 1
                        if debug:
                            print(f"✓ [{found_count}/{max_results}] 从缓存中找到结果: {link}")
                        yield cached_result
                        continue
                        
                    try:
                        # 保存到夸克网盘
                        if debug:
                            print(f"正在保存链接: {link}")
                        save_result = await self.quark_api.save_shared_file(link)
                        if not save_result.get("success"):
                            if debug:
                                print(f"× 保存失败: {save_result.get('message')}")
                            logging.warning(f"保存文件失败: {save_result.get('message')}")
                            continue
                            
                        result = {
                            "title": query,
                            "similarity": similarity,
                            "group_title": group_title,
                            "message_text": message.text,
                            "link": link,
                            "file_info": save_result.get("file_info", {}),
                            "message_date": message.date.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 更新缓存
                        self.cache.set(cache_key, result)
                        found_count += 1
                        if debug:
                            print(f"✓ [{found_count}/{max_results}] 找到新结果: {link}")
                        yield result
                        
                    except Exception as e:
                        if debug:
                            print(f"× 处理链接出错: {str(e)}")
                        logging.error(f"处理链接 {link} 时出错: {str(e)}")
                        continue
                    
            log_msg = f"群组 {group_title} 搜索完成，检查了 {message_count} 条消息，找到 {found_count} 个结果"
            logging.info(log_msg)
            if debug:
                print(f"\n{log_msg}")
                    
        except ChatAdminRequiredError:
            error_msg = f"需要管理员权限才能访问群组: {group}"
            logging.error(error_msg)
            if debug:
                print(f"\n× {error_msg}")
        except UserDeactivatedBanError:
            error_msg = f"账号被封禁，无法访问群组: {group}"
            logging.error(error_msg)
            if debug:
                print(f"\n× {error_msg}")
        except Exception as e:
            error_msg = f"搜索群组 {group} 时出错: {str(e)}"
            logging.error(error_msg, exc_info=True)
            if debug:
                print(f"\n× {error_msg}")
            
    async def search_messages_stream(
        self, 
        query: str, 
        min_similarity: int = 60,
        debug: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式搜索消息"""
        try:
            if not await self.connect_and_login():
                logging.error("无法连接到Telegram，搜索终止")
                return
                
            for group in self.target_groups:
                try:
                    if debug:
                        print(f"搜索群组: {group}")
                    async for result in self._search_group(group, query, min_similarity, debug):
                        yield result
                except Exception as e:
                    logging.error(f"搜索群组时出错: {str(e)}", exc_info=True)
                    if debug:
                        print(f"搜索群组 {group} 时出错: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"搜索消息时出错: {str(e)}", exc_info=True)
            if debug:
                print(f"搜索出错: {str(e)}")

    async def search_and_save(self, query: str, limit: int = 60) -> List[Dict[str, Any]]:
        """搜索并保存资源

        Args:
            query (str): 搜索关键词
            limit (int, optional): 搜索结果数量限制. Defaults to 60.

        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        # 先从缓存中查找
        cache_key = f"{query}_{limit}"
        cached_data = self.cache.get(cache_key)
        if cached_data and cached_data.get('results'):
            return cached_data['results']

        # 初始化结果列表
        results = []
        saved = False  # 是否已经保存成功

        # 搜索每个群组
        for group in self.target_groups:
            try:
                async for message in self.client.iter_messages(
                    group,
                    search=query,
                    limit=limit
                ):
                    try:
                        # 提取分享链接
                        links = re.findall(r'https://pan\.quark\.cn/s/[a-zA-Z0-9]+', message.text)
                        if not links:
                            continue

                        # 计算相似度
                        similarity = fuzz.ratio(query.lower(), message.text.lower())
                        
                        # 提取日期和群组信息
                        date = message.date.strftime("%Y-%m-%d %H:%M:%S")
                        group_title = group

                        # 如果还没有保存成功，尝试保存第一个链接
                        share_info = None
                        if not saved:
                            for link in links:
                                logger.debug(f"正在保存链接: {link}")
                                save_result = await self.quark_api.save_and_share(link)
                                if save_result.get("success"):
                                    saved = True
                                    share_info = save_result
                                    logger.debug(f"保存并分享成功: {link} -> {save_result['share_url']}")
                                    break
                                else:
                                    logger.error(f"保存并分享失败: {save_result}")

                        # 添加到结果集
                        description = ""
                        for line in message.text.split("\n"):
                            if line and "链接" not in line and "群组" not in line and "频道" not in line:
                                description += line
                                description += "\n"
                        description = description.strip()

                        result = {
                            "text": description,
                            "link": links[0],  # 原始链接
                            "similarity": similarity,
                            "date": date,
                            "group": group_title,
                            "message_id": message.id,
                        }

                        # 如果保存成功，添加保存后的信息
                        if share_info:  
                            result.update({
                                # "saved_file": share_info["saved_file"],
                                "share_url": share_info["share_url"]
                                # "share_pwd": share_info["share_info"].get("passcode"),
                            })
                            # 只有保存成功的, 才添加到结果集
                            results.append(result)

                        # 如果已经保存成功，就停止搜索
                        if saved:
                            break

                    except Exception as e:
                        logging.error(f"处理消息出错: {str(e)}", exc_info=True)
                        continue

                if saved:
                    break

            except Exception as e:
                logging.error(f"搜索群组时出错: {str(e)}", exc_info=True)
                continue

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # 缓存结果
        self.cache.set(cache_key, results)

        return results
