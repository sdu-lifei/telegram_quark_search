import itchat
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class WeChatSender:
    def __init__(self, target_groups: List[str]):
        """初始化微信发送器
        
        Args:
            target_groups (List[str]): 目标群组名称列表
        """
        self.target_groups = target_groups
        self.group_users = {}
        self._init_wechat()
        
    def _init_wechat(self):
        """初始化微信"""
        try:
            # 使用UOS协议登录，增加登录超时时间
            itchat.auto_login(
                enableCmdQR=2,
                hotReload=True,
                loginCallback=lambda: logger.info("微信登录成功"),
                exitCallback=lambda: logger.info("微信已退出"),
                statusStorageDir='./wechat.pkl'
            )
            
            # 等待5秒确保登录完成
            logger.info("等待微信初始化...")
            time.sleep(5)
            
            # 获取群组列表，最多重试5次
            for attempt in range(5):
                try:
                    # 更新群聊列表
                    logger.info(f"尝试 {attempt + 1}/5: 获取群组列表")
                    chatrooms = itchat.get_chatrooms(update=True)
                    if not chatrooms:
                        logger.warning(f"尝试 {attempt + 1}/5: 未获取到群组列表，等待3秒后重试")
                        time.sleep(3)
                        continue
                    
                    logger.info(f"获取到 {len(chatrooms)} 个群组")
                    
                    # 过滤目标群组
                    self.group_users = {}
                    for group in chatrooms:
                        if group['NickName'] in self.target_groups:
                            self.group_users[group['NickName']] = group['UserName']
                            logger.info(f"找到目标群: {group['NickName']}")
                    
                    if self.group_users:
                        logger.info(f"成功获取群组: {list(self.group_users.keys())}")
                        return
                    else:
                        logger.warning(f"未找到目标群组: {self.target_groups}")
                        logger.info(f"当前可用群组: {[group['NickName'] for group in chatrooms]}")
                        time.sleep(3)
                        
                except Exception as e:
                    logger.warning(f"尝试 {attempt + 1}/5 获取群组失败: {e}")
                    time.sleep(3)
                    
            if not self.group_users:
                raise ValueError(f"无法找到目标群组: {self.target_groups}")
                
        except Exception as e:
            logger.error(f"微信初始化失败: {e}")
            raise
    def format_results(self, results: List[Dict[str, Any]]):
        """打印格式化的结果"""
        message = ""
        for result in results:
            message += "\n" + "-"*20
            message += "\n" + result['text']
            message += "\n" + "🎬 " + result['search_results'][0]['text']
            message += "\n" + "🔗 分享链接: " + result['search_results'][0]['share_url']
            message += "\n" + "-"*20
        return message
    
    def format_result(self, result):
        """打印格式化的结果"""
        message = ""
        message += "\n" + "-"*40
        message += "\n" + result['text']
        message += "\n" + "🎬 " + result['search_results'][0]['text']
        message += "\n" + "🔗 分享链接: " + result['search_results'][0]['share_url']
        message += "\n" + "-"*40
        return message

    def send_to_groups(self, results: List[Dict[str, Any]]) -> bool:
        """发送结果到微信群
        
        Args:
            results (List[Dict[str, Any]]): 搜索结果列表
            
        Returns:
            bool: 是否发送成功
        """
        try:
            for group_name, group_id in self.group_users.items():
                logger.info(f"开始向群 {group_name} 发送消息")
                # message = self.format_results(results)
                # itchat.send(message, toUserName=group_id)
                for result in results:
                    # 发送文本消息
                    text = self.format_result(result)
                    itchat.send(text, toUserName=group_id)
                    
                    # # 如果有搜索结果，发送第一个结果的详细信息
                    # if result.get('search_results'):
                    #     first_result = result['search_results'][0]
                    #     detail_text = (
                    #         f"🎬 资源详情:\n"
                    #         f"{first_result['text']}\n\n"
                    #         f"🔗 分享链接:\n"
                    #         f"{first_result.get('share_url', first_result.get('link', '暂无链接'))}"
                    #     )
                        
            return True
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
            
    def close(self):
        """关闭微信连接"""
        itchat.logout()

def send_results_to_wechat(results: List[Dict[str, Any]], groups: List[str]) -> bool:
    """发送结果到微信群的便捷函数
    
    Args:
        results (List[Dict[str, Any]]): 搜索结果列表
        groups (List[str]): 目标群组名称列表
        
    Returns:
        bool: 是否发送成功
    """
    try:
        sender = WeChatSender(groups)
        success = sender.send_to_groups(results)
        sender.close()
        return success
    except Exception as e:
        logger.error(f"发送到微信失败: {e}")
        return False 