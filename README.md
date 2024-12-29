# 热门资源自动收集器

这是一个自动化工具，用于收集和分享热门影视资源。它会自动从百度热搜获取热门的电影、电视剧和小说，然后在Telegram资源群中搜索对应的网盘资源，并转存到夸克网盘，最后生成易于分享的格式。

## 功能特点

- 自动获取百度热搜榜的热门影视作品
- 支持电影、电视剧、小说三个分类
- 自动在Telegram群组中搜索资源
- 自动保存到夸克网盘
- 生成美观的分享格式
- 支持资源缓存，避免重复下载
- 完善的错误处理和重试机制

## 安装

1. 克隆项目：
```bash
git clone [项目地址]
cd telegram_quark_search
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置

1. 复制`.env.example`为`.env`：
```bash
cp .env.example .env
```

2. 在`.env`文件中填写必要的配置：
- `API_ID`: Telegram API ID
- `API_HASH`: Telegram API Hash
- `TARGET_GROUPS`: 要搜索的Telegram群组ID，多个用逗号分隔
- `QUARK_COOKIE`: 夸克网盘的Cookie

## 使用方法

1. 运行程序：
```bash
python main.py
```

2. 测试模式（只处理第一个热搜）：
```bash
python main.py --test
```

## 项目结构

```
telegram_quark_search/
├── src/
│   ├── baidu/           # 百度热搜相关
│   ├── telegram/        # Telegram搜索相关
│   ├── quark/          # 夸克网盘API
│   ├── utils/          # 工具函数
│   ├── config.py       # 配置管理
│   └── collector.py    # 主要收集逻辑
├── cache/              # 缓存目录
├── results/            # 结果保存目录
├── .env               # 环境变量
├── main.py            # 入口文件
└── requirements.txt    # 依赖清单
```

## 注意事项

- 请确保提供的Telegram API凭证有效
- 夸克网盘Cookie需要定期更新
- 建议使用代理以提高访问速度
- 建议定时运行以保持资源更新

## 许可证

MIT License
