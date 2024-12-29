import asyncio
import os
from dotenv import load_dotenv
from quark_save import QuarkSave
import logging
from src.utils.logger import setup_logger

# 设置日志为DEBUG级别
logger = setup_logger(level=logging.DEBUG)

async def main():
    # 加载环境变量
    load_dotenv()
    cookie = os.getenv('QUARK_COOKIE')
    if not cookie:
        raise ValueError("请在.env文件中设置QUARK_COOKIE")

    # 创建QuarkSave实例
    quark = QuarkSave(cookie)
    
    try:
        # 测试获取容量信息
        logger.debug("开始测试获取容量信息...")
        breakpoint()  # 第一个断点：获取容量信息前
        capacity = await quark.get_capacity()
        logger.info(f"网盘容量信息: {capacity}")

        # 测试获取文件列表
        logger.debug("开始测试获取文件列表...")
        breakpoint()  # 第二个断点：获取文件列表前
        files = await quark.get_file_list()
        logger.info(f"文件列表: {files[:2]}")  # 只显示前两个文件

        # 测试保存并分享文件
        share_url = input("请输入要测试的分享链接: ")
        logger.debug(f"开始测试保存并分享文件: {share_url}")
        breakpoint()  # 第三个断点：保存分享前
        result = await quark.save_and_share(share_url)
        logger.info(f"保存并分享结果: {result}")

    finally:
        await quark.close()

if __name__ == "__main__":
    asyncio.run(main()) 