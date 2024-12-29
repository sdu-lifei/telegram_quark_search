import logging
import sys
from typing import Optional

def setup_logger(level: int = logging.DEBUG, name: Optional[str] = None) -> logging.Logger:
    """设置统一的日志配置

    Args:
        level: 日志级别，默认为DEBUG
        name: 日志记录器名称，默认为None（使用根记录器）

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 配置控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)  # 确保处理器也使用相同的日志级别

    # 配置文件输出
    file_handler = logging.FileHandler('app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)  # 确保处理器也使用相同的日志级别

    # 获取或创建日志记录器
    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(level)
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    # 添加新的处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 设置特定模块的日志级别
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # 确保日志可以传播
    logger.propagate = True

    return logger