import asyncio
import logging
import argparse
import sys
from src.collector import ResourceCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('collector.log'),
        logging.StreamHandler()
    ]
)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='热门资源收集器')
    parser.add_argument('--test', action='store_true', help='测试模式，只处理第一个热搜项目')
    parser.add_argument('--debug', action='store_true', help='调试模式，显示更多信息')
    args = parser.parse_args()
    
    print("\n=== 热门资源收集器 ===")
    print("正在启动...")
    
    # 初始化资源收集器
    collector = ResourceCollector()
    
    try:
        # 初始化
        if not await collector.init():
            logging.error("初始化失败")
            return
            
        print("\n1. 获取热搜榜...")
        results = await collector.collect_resources(test_mode=args.test, debug=args.debug)
        
        if results:
            print("\n✅ 收集完成！找到以下资源：")
            collector.print_results(results)
        else:
            print("\n⚠️ 未找到任何资源")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 程序被用户中断")
        print("正在清理资源...")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        logging.error(f"程序出错: {str(e)}", exc_info=True)
    finally:
        try:
            print("\n正在关闭连接...")
            await collector.close()
            print("已安全退出")
        except Exception as e:
            logging.error(f"关闭连接时出错: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
