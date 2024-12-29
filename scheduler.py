import schedule
import time
import asyncio
import logging
from datetime import datetime
from main import main

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

async def job():
    """定时任务"""
    logging.info(f"开始执行定时任务 - {datetime.now()}")
    try:
        await main()
    except Exception as e:
        logging.error(f"任务执行出错: {str(e)}")
    logging.info(f"定时任务完成 - {datetime.now()}")

def run_job():
    """运行异步任务的包装函数"""
    asyncio.run(job())

def run_scheduler():
    """启动定时任务调度器"""
    # 设置每天早上7点运行
    schedule.every().day.at("07:00").do(run_job)
    
    logging.info("定时任务已启动")
    
    # 立即运行一次（测试用）
    run_job()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    run_scheduler() 