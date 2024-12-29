import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 加载环境变量
env_path = ROOT_DIR / '.env'
load_dotenv(env_path)

# 验证环境变量
required_vars = ['API_ID', 'API_HASH', 'TARGET_GROUPS', 'QUARK_COOKIE']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"请在.env文件中设置{var}")

# Telegram配置
TELEGRAM_CONFIG = {
    'API_ID': int(os.getenv('API_ID')),
    'API_HASH': os.getenv('API_HASH'),
    'TARGET_GROUPS': os.getenv('TARGET_GROUPS', '').split(','),
    'MAX_RESULTS': int(os.getenv('MAX_RESULTS', '100'))
}

# 夸克网盘配置
QUARK_CONFIG = {
    'COOKIE': os.getenv('QUARK_COOKIE'),
    'BASE_URL': "https://drive-pc.quark.cn",
    'MAX_RETRIES': 5,  # 增加重试次数
    'RETRY_DELAY': 2.0  # 增加重试延迟（秒）
}

# 缓存配置
CACHE_CONFIG = {
    'DIR': ROOT_DIR / "cache",
    'SEARCH_CACHE_FILE': ROOT_DIR / "cache" / "search_cache.json",
    'EXPIRE_DAYS': 7
}

# 结果配置
RESULTS_CONFIG = {
    'DIR': ROOT_DIR / "results",
    'LATEST_FILE': ROOT_DIR / "results" / "latest.json"
}

# 创建必要的目录
for dir_path in [CACHE_CONFIG['DIR'], RESULTS_CONFIG['DIR']]:
    dir_path.mkdir(exist_ok=True)

# 微信配置
WECHAT_CONFIG = {
    'TARGET_GROUPS': os.getenv('WECHAT_GROUPS', '').split(','),  # 目标群组名称列表，用逗号分隔
    'ENABLED': os.getenv('WECHAT_ENABLED', 'false').lower() == 'true'  # 是否启用微信发送
}

# V2Ray配置
V2RAY_CONFIG = {
    'ENABLED': os.getenv('V2RAY_ENABLED', 'true').lower() == 'true',
    'PATH': os.getenv('V2RAY_PATH', 'v2ray'),
    'CONFIG': os.getenv('V2RAY_CONFIG', './v2ray.json'),
    'SUB_URL': os.getenv('V2RAY_SUB_URL', '')  # V2Ray订阅地址
}
