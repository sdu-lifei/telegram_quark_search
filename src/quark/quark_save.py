import aiohttp
import logging
import json
import re
from typing import Dict, Any, Optional, List
import time
import asyncio
from src.utils.logger import setup_logger

# 设置日志为DEBUG级别
logger = setup_logger(level=logging.DEBUG)

class QuarkSave:
    def __init__(self, cookie: str):
        """初始化夸克网盘 API

        Args:
            cookie (str): 夸克网盘 cookie
        """
        self.cookie = cookie
        self.session = aiohttp.ClientSession()
        self.BASE_URL = "https://drive-pc.quark.cn"
        logger.debug("QuarkSave initialized with BASE_URL: %s", self.BASE_URL)

    async def close(self):
        """关闭会话"""
        await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Cookie': self.cookie,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://pan.quark.cn',
            'Referer': 'https://pan.quark.cn/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'drive-pc.quark.cn'
        }

    async def _request(self, method: str, url: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """发送请求

        Args:
            method (str): 请求方法
            url (str): 请求地址
            data (Optional[Dict]): 请求数据

        Returns:
            Dict[str, Any]: 响应结果
        """
        try:
            params = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": ""
            }

            logger.debug("发送请求: %s %s", method, url)
            logger.debug("请求参数: %s", params)
            logger.debug("请求数据: %s", data)
            logger.debug("请求头: %s", self._get_headers())

            async with self.session.request(
                method,
                url,
                params=params,
                json=data,
                headers=self._get_headers()
            ) as response:
                result = await response.json()
                logger.debug("响应结果: %s", result)
                return result
        except Exception as e:
            logger.exception("请求出错: %s", str(e))
            return {"code": -1, "message": str(e)}

    async def get_file_list(self, pdir_fid: str = "0") -> List[Dict[str, Any]]:
        """获取文件列表

        Args:
            pdir_fid (str): 父目录ID

        Returns:
            List[Dict[str, Any]]: 文件列表
        """
        url = f"{self.BASE_URL}/1/clouddrive/file/list"
        data = {
            "pdir_fid": pdir_fid,
            "force": 0,
            "_page": 1,
            "_size": 50,
            "_fetch_total": 1,
            "_sort": "file_type:asc,updated_at:desc"
        }

        result = await self._request("GET", url, data)
        if result.get("code") == 0:
            return result["data"]["list"]
        return []

    async def get_file_info(self, fid: str) -> Optional[Dict[str, Any]]:
        """获取文件信息

        Args:
            fid (str): 文件ID

        Returns:
            Optional[Dict[str, Any]]: 文件信息
        """
        url = f"{self.BASE_URL}/1/clouddrive/file/info"
        data = {
            "fid": fid,
            "pdir_fid": "0",
            "force": 0
        }

        result = await self._request("GET", url, data)
        if result.get("code") == 0:
            return result["data"]
        return None

    async def save(self, share_url: str) -> Dict[str, Any]:
        """保存分享文件

        Args:
            share_url (str): 分享链接

        Returns:
            Dict[str, Any]: 保存结果
        """
        try:
            # 1. 提取pkey
            pkey = share_url.split('/')[-1].strip(']')
            logger.debug(f"提取的pkey: {pkey}")

            # 2. 获取stoken
            token_url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/token"
            token_data = {
                "pwd_id": pkey,
                "passcode": ""
            }
            token_result = await self._request("POST", token_url, token_data)
            if token_result.get("code") != 0:
                return {"success": False, "message": f"获取token失败: {token_result.get('message')}"}

            stoken = token_result["data"]["stoken"]

            # 3. 获取文件信息
            info_url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail"
            info_data = {
                "pwd_id": pkey,
                "stoken": stoken,
                "pdir_fid": "0"
            }
            info_result = await self._request("GET", info_url, info_data)
            if info_result.get("code") != 0:
                return {"success": False, "message": f"获取文件信息失败: {info_result.get('message')}"}

            file_info = info_result["data"]["list"][0]
            fid = file_info["fid"]
            fid_token = file_info["share_fid_token"]

            # 4. 保存文件
            save_url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/save"
            save_data = {
                "fid_list": [fid],
                "fid_token_list": [fid_token],
                "to_pdir_fid": "0",
                "pwd_id": pkey,
                "stoken": stoken,
                "pdir_fid": "0",
                "scene": "link"
            }
            save_result = await self._request("POST", save_url, save_data)
            if save_result.get("code") != 0:
                return {"success": False, "message": f"保存文件失败: {save_result.get('message')}"}

            return {"success": True, "fid": fid}

        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return {"success": False, "message": str(e)}

    async def share(self, fid: str) -> Dict[str, Any]:
        """分享文件

        Args:
            fid (str): 文件ID

        Returns:
            Dict[str, Any]: 分享结果
        """
        try:
            # 1. 创建分享
            share_url = f"{self.BASE_URL}/1/clouddrive/share"
            share_data = {
                "fid_list": [fid],
                "share_type": "file",
                "share_channel": "web",
                "expired_type": 0,
                "share_from": "pc",
                "scene": "link"
            }

            share_result = await self._request("POST", share_url, share_data)
            if share_result.get("code") != 0:
                return {"success": False, "message": f"创建分享失败: {share_result.get('message')}"}

            share_id = share_result["data"]["share_id"]

            # 2. 获取分享密码
            password_url = f"{self.BASE_URL}/1/clouddrive/share/password"
            password_data = {
                "share_id": share_id,
                "scene": "link"
            }

            password_result = await self._request("POST", password_url, password_data)
            if password_result.get("code") != 0:
                return {"success": False, "message": f"获取分享密码失败: {password_result.get('message')}"}

            pwd_id = password_result["data"]["pwd_id"]
            share_url = f"https://pan.quark.cn/s/{pwd_id}"

            return {
                "success": True,
                "share_url": share_url,
                "share_id": share_id,
                "pwd_id": pwd_id
            }

        except Exception as e:
            logger.error(f"分享文件失败: {str(e)}")
            return {"success": False, "message": str(e)}

    async def save_and_share(self, share_url: str) -> Dict[str, Any]:
        """保存并分享文件

        Args:
            share_url (str): 分享链接

        Returns:
            Dict[str, Any]: 保存和分享结果
        """
        # 1. 保存文件
        save_result = await self.save(share_url)
        if not save_result["success"]:
            return save_result

        # 2. 分享文件
        share_result = await self.share(save_result["fid"])
        if not share_result["success"]:
            return share_result

        return {
            "success": True,
            "original_url": share_url,
            "share_url": share_result["share_url"]
        }

    async def get_capacity(self) -> Dict[str, Any]:
        """获取网盘容量信息"""
        url = f"{self.BASE_URL}/1/clouddrive/capacity"
        result = await self._request("GET", url)
        if result.get("code") == 0:
            return result["data"]
        return {} 