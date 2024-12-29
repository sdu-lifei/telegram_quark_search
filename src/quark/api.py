import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any
import time
import re
from src.utils.logger import setup_logger

# 设置日志
logger = setup_logger(level=logging.WARNING)  # 默认使用INFO级别

class QuarkAPI:
    """夸克网盘 API"""

    def __init__(self, cookie: str):
        """初始化夸克网盘 API

        Args:
            cookie (str): 夸克网盘 cookie
        """
        self.cookie = cookie
        self.session = aiohttp.ClientSession()
        self.mparam = self._match_mparam_form_cookie(cookie)
        self.BASE_URL = "https://drive-pc.quark.cn"
        self.BASE_URL_APP = "https://drive-m.quark.cn"
        self.USER_AGENT = "Mozilla/5.0 (Linux; Android 13; M2011K2C Build/TKQ1.220829.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/111.0.5563.116 Mobile Safari/537.36 quark/7.4.5.680 ucpro/7.4.5.680"
        
        # 验证账号是否有效
        if "__uid" not in cookie:
            raise ValueError("cookie 无效，缺少必要参数 __uid")

    def _match_mparam_form_cookie(self, cookie):
        """从 cookie 中取 mparam 参数"""
        mparam = {}
        kps_match = re.search(r"(?<!\w)kps=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        sign_match = re.search(r"(?<!\w)sign=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        vcode_match = re.search(r"(?<!\w)vcode=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        if kps_match and sign_match and vcode_match:
            mparam = {
                "kps": kps_match.group(1).replace("%25", "%"),
                "sign": sign_match.group(1).replace("%25", "%"),
                "vcode": vcode_match.group(1).replace("%25", "%"),
            }
        return mparam

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头

        Returns:
            Dict[str, str]: 请求头
        """
        return {
            'Cookie': self.cookie,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://pan.quark.cn',
            'Referer': 'https://pan.quark.cn/',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site'
        }

    def _get_app_headers(self) -> Dict[str, str]:
        """获取 app 端请求头

        Returns:
            Dict[str, str]: app 端请求头
        """
        return {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
        }

    def _get_app_params(self) -> Dict[str, str]:
        """获取 app 端请求参数

        Returns:
            Dict[str, str]: app 端请求参数
        """
        return {
            "device_model": "M2011K2C",
            "entry": "default_clouddrive",
            "_t_group": "0%3A_s_vp%3A1",
            "dmn": "Mi%2B11",
            "fr": "android",
            "pf": "3300",
            "bi": "35937",
            "ve": "7.4.5.680",
            "ss": "411x875",
            "mi": "M2011K2C",
            "nt": "5",
            "nw": "0",
            "kt": "4",
            "pr": "ucpro",
            "sv": "release",
            "dt": "phone",
            "data_from": "ucapi",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
            "app": "clouddrive",
            "kkkk": "1",
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        use_app: bool = False,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """发送请求

        Args:
            method (str): 请求方法
            url (str): 请求地址
            params (Optional[Dict[str, Any]], optional): 请求参数. Defaults to None.
            json (Optional[Dict[str, Any]], optional): 请求体. Defaults to None.
            headers (Optional[Dict[str, str]], optional): 请求头. Defaults to None.
            timeout (int, optional): 超时时间. Defaults to 30.
            use_app (bool, optional): 是否使用 app 端 API. Defaults to False.
            retry_count (int, optional): 重试次数. Defaults to 3.

        Returns:
            Dict[str, Any]: 响应结果
        """
        if params is None:
            params = {}
        if headers is None:
            headers = self._get_headers()

        if use_app and self.mparam and "share" in url and self.BASE_URL in url:
            # 使用 app 端 API
            url = url.replace(self.BASE_URL, self.BASE_URL_APP)
            params.update(self._get_app_params())
            headers = self._get_app_headers()
        else:
            # 只在非APP请求时添加这些参数
            params.update({
                "pr": "ucpro",
                "fr": "pc",
            })

        # 添加通用参数
        params.update({
            "__dt": int(time.time() * 1000),
            "__t": int(time.time()),
            "uc_param_str": ""
        })

        last_error = None
        for attempt in range(retry_count):
            try:
                logger.debug(f"发送请求: {method} {url}")
                logger.debug(f"请求参数: {params}")
                logger.debug(f"请求体: {json}")
                
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=client_timeout,
                ) as response:
                    result = await response.json()
                    logger.debug(f"响应结果: {result}")
                    
                    if result.get("code") == 31001:  # require login
                        logger.error(f"请求需要登录: {url}")
                        logger.debug(f"请求头: {headers}")
                        logger.debug(f"请求参数: {params}")
                        logger.debug(f"请求体: {json}")
                        logger.debug(f"响应: {result}")
                    return result

            except asyncio.TimeoutError as e:
                last_error = f"请求超时: {str(e)}"
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"请求超时，等待{wait_time}秒后重试 ({attempt + 1}/{retry_count})")
                    await asyncio.sleep(wait_time)
                    continue

            except Exception as e:
                last_error = str(e)
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"请求出错，等待{wait_time}秒后重试 ({attempt + 1}/{retry_count}): {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue

        logger.error(f"请求失败，已重试{retry_count}次: {last_error}")
        return {"code": -1, "message": f"请求出错: {last_error}"}

    async def init(self) -> bool:
        """初始化并验证账号

        Returns:
            bool: 是否验证成功
        """
        try:
            account_info = await self.get_account_info()
            if not account_info:
                logger.error("账号登录失败，cookie 无效")
                return False
            logger.info(f"账号登录成功，昵称: {account_info['nickname']}")
            return True
        except Exception as e:
            logger.error(f"账号验证失败: {str(e)}")
            return False

    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账号信息

        Returns:
            Optional[Dict[str, Any]]: 账号信息
        """
        url = "https://pan.quark.cn/account/info"
        params = {
            "fr": "pc",
            "platform": "pc",
        }
        
        result = await self._request("GET", url, params=params)
        if result.get("data"):
            return result["data"]
        return None

    async def save_shared_file(self, share_url: str) -> Dict[str, Any]:
        """保存分享的文件到自己的网盘

        Args:
            share_url (str): 分享链接

        Returns:
            Dict[str, Any]: 响应结果
        """
        try:
            # 获取分享 ID
            pwd_id = re.search(r'/s/([^/\s?]+)', share_url)
            if not pwd_id:
                return {"success": False, "message": "无效的分享链接"}
            pwd_id = pwd_id.group(1)

            # 获取 stoken
            stoken_result = await self._request(
                "POST",
                f"{self.BASE_URL}/1/clouddrive/share/sharepage/token",
                params={
                    "pr": "ucpro",
                    "fr": "pc",
                },
                json={
                    "pwd_id": pwd_id,
                    "passcode": "",
                },
                use_app=False,
            )
            if stoken_result.get("status") != 200:
                return {"success": False, "message": f"获取文件信息失败: {stoken_result.get('message')}"}
            stoken = stoken_result["data"]["stoken"]

            # 获取文件列表
            detail_result = await self._request(
                "GET",
                f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail",
                params={
                    "pr": "ucpro",
                    "fr": "pc",
                    "pwd_id": pwd_id,
                    "stoken": stoken,
                    "pdir_fid": "0",
                    "force": "0",
                    "_page": 1,
                    "_size": "50",
                    "_fetch_total": "1",
                    "_sort": "file_type:asc,updated_at:desc",
                },
                use_app=False,
            )
            if detail_result.get("code") != 0:
                return {"success": False, "message": f"获取文件列表失败: {detail_result.get('message')}"}

            # 保存文件
            file_info = detail_result["data"]["list"][0]
            fid = file_info["fid"]
            fid_token = file_info["share_fid_token"]

            save_result = await self._request(
                "POST",
                f"{self.BASE_URL}/1/clouddrive/share/sharepage/save",
                params={
                    "pr": "ucpro",
                    "fr": "pc",
                },
                json={
                    # "fid_list": [item["fid"] for item in detail_result["data"]["list"]],
                    # "fid_token_list": [item["share_fid_token"] for item in detail_result["data"]["list"]],
                    "fid_list": [fid],
                    "fid_token_list": [fid_token],
                    "to_pdir_fid": "0",
                    "pwd_id": pwd_id,
                    "stoken": stoken,
                    "pdir_fid": "0",
                    "scene": "link",
                },
                use_app=False,
            )
            logger.debug(f"保存文件结果: {save_result}")
            if save_result.get("code") != 0:
                return {"success": False, "message": f"保存文件失败: {save_result}"}

            # return {"success": True, "fid": fid}
            # 等待任务完成
            task_id = save_result["data"]["task_id"]
            task_result = await self.query_task(task_id)
            if task_result.get("code") != 0:
                return {"success": False, "message": f"任务执行失败: {task_result.get('message')}"}

            # 从任务结果中获取保存后的文件ID
            if not task_result.get("data", {}).get("save_as", {}).get("save_as_top_fids"):
                return {"success": False, "message": "无法获取保存后的文件ID"}
            saved_fid = task_result["data"]["save_as"]["save_as_top_fids"][0]
            logger.debug(f"原文件:{fid}, 获取到保存后的文件ID: {saved_fid}")
            return {"success": True, "fid": saved_fid}
            # # 等待2秒确保文件保存完成
            # await asyncio.sleep(2)

            # # 创建分享链接
            # share_result = await self._request(
            #     "POST",
            #     f"{self.BASE_URL}/1/clouddrive/share",
            #     params={
            #         "pr": "ucpro",
            #         "fr": "pc",
            #     },
            #     json={
            #         "fid_list": [saved_fid],
            #         "expired_type": "forever",
            #         "share_channel": "link",
            #         "share_from": "pc_client",
            #         "scene": "link",
            #         "title": "",
            #         "passcode": "",
            #         "url_type": 0
            #     },
            #     use_app=False,
            # )
            # if share_result.get("code") != 0:
            #     return {"success": False, "message": f"创建分享链接失败: {share_result}"}

            # # 等待分享任务完成
            # share_task_id = share_result["data"]["task_id"]
            # share_task_result = await self.query_task(share_task_id)
            # if share_task_result.get("code") != 0:
            #     return {"success": False, "message": f"分享任务失败: {share_task_result.get('message')}"}

            # # 从任务结果中获取share_id
            # if not share_task_result.get("data", {}).get("share_id"):
            #     return {"success": False, "message": "无法获取分享ID"}
            # share_id = share_task_result["data"]["share_id"]

            # # 获取分享密码
            # password_result = await self._request(
            #     "POST",
            #     f"{self.BASE_URL}/1/clouddrive/share/password",
            #     params={
            #         "pr": "ucpro",
            #         "fr": "pc",
            #     },
            #     json={
            #         "share_id": share_id,
            #         "scene": "link"
            #     },
            #     use_app=False,
            # )
            # if password_result.get("code") != 0:
            #     return {"success": False, "message": f"获取分享密码失败: {password_result}"}

            # # 构建分享链接
            # pwd_id = password_result["data"]["pwd_id"]
            # share_url = f"https://pan.quark.cn/s/{pwd_id}"

            # return {
            #     "success": True,
            #     "message": "文件保存并分享成功",
            #     "share_url": share_url
            # }

        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}", exc_info=True)
            return {"success": False, "message": f"保存文件失败: {str(e)}"}

    async def query_task(self, task_id: str, max_retries: int = 5) -> Dict[str, Any]:
        """查询任务状态，支持重试"""
        # if max_retries is None:
        #     max_retries = 5
            
        logger.debug(f"开始查询任务状态: {task_id}")
        retry_count = 0
        retry_index = 0
        
        while True:
            try:
                url = f"{self.BASE_URL}/1/clouddrive/task"
                params = {
                    "pr": "ucpro",
                    "fr": "pc",
                    "task_id": task_id,
                    "retry_index": retry_index,
                    "__dt": int(time.time() * 1000),
                    "__t": int(time.time()),
                    "uc_param_str": ""
                }
                
                headers = {
                    'Cookie': self.cookie,
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Origin': 'https://pan.quark.cn',
                    'Referer': 'https://pan.quark.cn/',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-site'
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    result = await response.json()
                    logger.debug(f"任务查询响应: {result}")
                    
                    if result.get("code") != 0:
                        if retry_count < max_retries:
                            retry_count += 1
                            await asyncio.sleep(1)
                            continue
                        logger.error(f"查询任务失败: {result}")
                        return {"code": -1, "message": result.get('message')}
                    
                    task_status = result["data"]["status"]
                    if task_status != 0:  # 非进行中状态
                        return result
                    
                    retry_index += 1
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                if retry_count < max_retries:
                    retry_count += 1
                    await asyncio.sleep(1)
                    continue
                logger.error(f"查询任务状态出错: {str(e)}", exc_info=True)
                return {"code": -1, "message": str(e)}

    async def close(self):
        """关闭会话"""
        await self.session.close()

    # async def get_saved_file_info(self, fid: str) -> Dict[str, Any]:
    #     """获取保存的文件信息

    #     Args:
    #         fid (str): 文件 ID

    #     Returns:
    #         Dict[str, Any]: 文件信息
    #     """
    #     try:
    #         result = await self._request(
    #             "GET",
    #             f"{self.BASE_URL}/1/clouddrive/file/info",
    #             params={
    #                 "pr": "ucpro",
    #                 "fr": "pc",
    #                 "fid": fid,
    #                 "pdir_fid": "0",
    #                 "force": "0",
    #             },
    #             use_app=False,  # 使用 PC 端 API
    #         )
    #         if result.get("code") != 0:
    #             return {"success": False, "message": f"获取文件信息失败: {result.get('message')}"}

    #         return {
    #             "success": True,
    #             "message": "获取文件信息成功",
    #             "data": result["data"]
    #         }
    #     except Exception as e:
    #         logger.error(f"获取文件信息失败: {str(e)}", exc_info=True)
    #         return {"success": False, "message": f"获取文件信息失败: {str(e)}"}

    # async def create_share_link(self, fid: str) -> Dict[str, Any]:
    #     """创建分享链接

    #     Args:
    #         fid (str): 文件 ID

    #     Returns:
    #         Dict[str, Any]: 分享信息
    #     """
    #     try:
    #         result = await self._request(
    #             "POST",
    #             f"{self.BASE_URL}/1/clouddrive/share/create",
    #             params={
    #                 "pr": "ucpro",
    #                 "fr": "pc",
    #             },
    #             json={
    #                 "fid_list": [fid],
    #                 "expiration": "forever",  # 永久有效
    #                 "share_type": "url",
    #                 "share_channel": "link",
    #             },
    #             use_app=False,  # 使用 PC 端 API
    #         )
    #         if result.get("code") != 0:
    #             return {"success": False, "message": f"创建分享链接失败: {result.get('message')}"}

    #         return {
    #             "success": True,
    #             "message": "创建分享链接成功",
    #             "data": result["data"]
    #         }
    #     except Exception as e:
    #         logger.error(f"创建分享链接失败: {str(e)}", exc_info=True)
    #         return {"success": False, "message": f"创建分享链接失败: {str(e)}"}

    async def save_and_share(self, share_url: str) -> Dict[str, Any]:
        """保���并分享文件

        Args:
            share_url (str): 分享链接

        Returns:
            Dict[str, Any]: 保存和分享结果
        """
        try:
            # 先保存文件
            save_result = await self.save_shared_file(share_url)
            if not save_result.get("success"):
                return save_result

            # 等待2秒确保文件保存完成
            await asyncio.sleep(0.5)

            # # 从任务结果中获取保存后的文件ID
            # task_result = save_result.get("task_result", {})
            # if not task_result or not task_result.get("data", {}).get("save_as", {}).get("save_as_top_fids"):
            #     logger.error(f"无法获取保存后的文件ID, task_result: {task_result}")
            #     return {"success": False, "message": "无法获取保存后的文件ID"}
            
            # saved_fid = task_result["data"]["save_as"]["save_as_top_fids"][0]
            saved_fid = save_result["fid"]
            logger.debug(f"获取到保存后的文件ID: {saved_fid}")

            # 创建新的分享链接
            share_result = await self.share_file(saved_fid)
            if not share_result.get("success"):
                logger.error(f"创建分享链接失败: {share_result}")
                return share_result

            return {
                "success": True,
                "message": "文件保存并分享成功",
                "original_url": share_url,
                "share_url": share_result.get("share_url")
            }
        except Exception as e:
            logger.error(f"保存并分享文件失败: {str(e)}", exc_info=True)
            return {"success": False, "message": f"保存并分享文件失败: {str(e)}"}

    async def share_file(self, fid: str) -> dict:
        """分享自己网盘中的文件"""
        try:
            logger.debug(f"开始分享文件, fid: {fid}")
            
            # 1. 创建分享任务
            logger.debug("创建分享任务...")
            share_url = f"{self.BASE_URL}/1/clouddrive/share"
            
            params = {
                "pr": "ucpro",
                "fr": "pc",
                "__dt": int(time.time() * 1000),
                "__t": int(time.time()),
                "uc_param_str": ""
            }
            
            data = {
                "fid_list": [fid],
                "expired_type": "1",
                "share_channel": "web",
                "share_from": "pc_web",
                "scene": "link",
                "title": "",
                "passcode": "",
                "url_type": 1
            }
            
            logger.debug(f"分享请求数据: {data}")
            share_result = await self._request("POST", share_url, params=params, json=data)
            
            if share_result.get("code") != 0:
                return {"success": False, "message": f"创建分享失败: {share_result.get('message')}"}

            # 等待分享任务完成
            share_task_id = share_result["data"]["task_id"]
            share_task_result = await self.query_task(share_task_id)
            if share_task_result.get("code") != 0:
                return {"success": False, "message": f"分享任务失败: {share_task_result.get('message')}"}

            # 从任务结果中获取share_id
            if not share_task_result.get("data", {}).get("share_id"):
                return {"success": False, "message": "无法获取分享ID"}
            share_id = share_task_result["data"]["share_id"]
            # share_id = share_result["data"]["share_id"]
            await asyncio.sleep(1)  # 等待1秒再获取分享密码

            # 2. 获取分享密码
            password_url = f"{self.BASE_URL}/1/clouddrive/share/password"
            password_data = {
                "share_id": share_id,
                "scene": "link"
            }

            password_result = await self._request("POST", password_url, json=password_data)
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
            logger.error(f"分享文件失败: {str(e)}", exc_info=True)
            return {"success": False, "message": f"分享出错: {str(e)}"}

    async def save_shared_file_internal(self, share_url: str) -> dict:
        """保存分享的文件到自己的网盘（内部方法）"""
        logger.debug(f"开始处理分享链接: {share_url}")
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
            logger.debug(f"请求stoken, URL: {token_url}, 数据: {token_data}")
            
            async with self.session.post(token_url, headers=self._get_headers(), params={"pr": "ucpro", "fr": "pc"}, json=token_data) as token_response:
                token_result = await token_response.json()
                logger.debug(f"stoken响应: {token_result}")
                
                # 检查链接否失效
                if token_result.get("status") == 404 or token_result.get("code") == 41011:
                    logger.error("分享链接已失效")
                    return {"success": False, "message": "分享链接已失效", "code": 41011}
                
                if token_result.get("code") != 0:
                    logger.error(f"获取token失败: {token_result}")
                    return {"success": False, "message": f"获取token失败: {token_result.get('message')}", "code": token_result.get("code")}
                
                stoken = token_result["data"]["stoken"]

            # 3. 获取文件信息
            info_url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail"
            params = {
                "pr": "ucpro",
                "fr": "pc",
                "pwd_id": pkey,
                "stoken": stoken,
                "pdir_fid": "0"
            }
            logger.debug(f"请求文件信息, URL: {info_url}, 参数: {params}")
            
            async with self.session.get(info_url, headers=self._get_headers(), params=params) as response:
                info_result = await response.json()
                logger.debug(f"文件信息响应: {info_result}")
                
                if info_result.get("code") != 0:
                    logger.error(f"获取文件信息失败: {info_result}")
                    return {"success": False, "message": f"获取文件信息失败: {info_result.get('message')}"}
                
                file_info = info_result["data"]["list"][0]
                fid = file_info["fid"]
                fid_token = file_info["share_fid_token"]
                logger.debug(f"获取到文件ID: {fid}, token: {fid_token}")

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
            logger.debug(f"保存文件请求, URL: {save_url}, 数据: {save_data}")
            
            async with self.session.post(save_url, headers=self._get_headers(), params={"pr": "ucpro", "fr": "pc"}, json=save_data) as response:
                save_result = await response.json()
                logger.debug(f"保存文件响应: {save_result}")
                
                if save_result.get("code") != 0:
                    logger.error(f"保存文件失败: {save_result}")
                    return {"success": False, "message": f"保存文件失败: {save_result.get('message')}"}
                
                task_id = save_result["data"]["task_id"]
                logger.debug(f"获取到保存任务ID: {task_id}")
                
                # 5. 查询任务状态
                task_result = await self.query_task(task_id)
                if task_result.get("code") != 0:
                    logger.error(f"保存任务失败: {task_result}")
                    return {"success": False, "message": f"任务执行失败: {task_result.get('message')}"}
                
                return {
                    "success": True,
                    "message": "文件保存成功",
                    "task_result": task_result
                }

        except Exception as e:
            logger.error(f"保存文件过程出错: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
