import subprocess
import logging
import json
import time
import os
import base64
import requests
import urllib.parse
from pathlib import Path

logger = logging.getLogger(__name__)

def parse_vless_link(link: str) -> dict:
    """解析VLESS链接
    
    Args:
        link (str): VLESS链接
        
    Returns:
        dict: VLESS配置
    """
    # 移除 "vless://" 前缀和备注
    vless_url = link[8:].split('#')[0]
    
    # 分离UUID和服务器信息
    uuid, server_part = vless_url.split('@', 1)
    
    # 分离服务器地址和参数
    if '?' in server_part:
        server_address, params_str = server_part.split('?', 1)
        # 解析URL编码的参数
        params = dict(urllib.parse.parse_qsl(params_str))
    else:
        server_address = server_part
        params = {}
    
    # 分离主机和端口
    host, port = server_address.split(':')
    
    # 构建outbound配置
    outbound = {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": host,
                "port": int(port),
                "users": [{
                    "id": uuid,
                    "encryption": params.get("encryption", "none"),
                    "flow": params.get("flow", "")
                }]
            }]
        },
        "streamSettings": {
            "network": params.get("type", "tcp"),
            "security": params.get("security", "none"),
            "tlsSettings": {
                "serverName": params.get("sni", host),
                "fingerprint": params.get("fp", "chrome"),
                "allowInsecure": True,
                "disableSystemRoot": False,
                "alpn": ["h2", "http/1.1"],
                "minVersion": "1.2",
                "maxVersion": "1.3",
                "cipherSuites": "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256:TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256:TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256:TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
            } if params.get("security") == "tls" else None,
            "wsSettings": {
                "path": urllib.parse.unquote(params.get("path", "/")),
                "headers": {
                    "Host": params.get("host", host)
                }
            } if params.get("type") == "ws" else None
        }
    }
    
    return outbound

class V2RayController:
    def __init__(self, config_path: str = None, v2ray_path: str = None, subscription_url: str = None):
        """初始化V2Ray控制器"""
        self.config_path = config_path or os.getenv('V2RAY_CONFIG', './v2ray.json')
        v2ray_base = v2ray_path or os.getenv('V2RAY_PATH', './static')
        # 确保使用完整的可执行文件路径
        self.v2ray_path = os.path.join(os.path.abspath(v2ray_base), 'v2ray')
        self.subscription_url = subscription_url or os.getenv('V2RAY_SUB_URL')
        self.process = None
        
        # 确保v2ray可执行文件存在
        if not os.path.exists(self.v2ray_path):
            raise FileNotFoundError(f"V2Ray可执行文件不存在: {self.v2ray_path}")
            
        # 确保有执行权限
        if not os.access(self.v2ray_path, os.X_OK):
            os.chmod(self.v2ray_path, 0o755)
            logger.info(f"已添加执行权限: {self.v2ray_path}")
        
    def update_config(self) -> bool:
        """从订阅地址更新配置"""
        try:
            if not self.subscription_url:
                logger.warning("未设置订阅地址")
                return False
                
            logger.info(f"正在从 {self.subscription_url} 更新V2Ray配置...")
            
            # 获取订阅内容
            response = requests.get(self.subscription_url, timeout=10)
            if response.status_code != 200:
                logger.error(f"获取订阅失败: {response.status_code}")
                return False
            
            # 打印原始响应内容的前100个字符（用于调试）
            logger.debug(f"原始响应内容: {response.text[:100]}...")
            
            # 创建基础配置
            config = {
                "inbounds": [{
                    "port": 1080,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "udp": True
                    }
                }],
                "outbounds": []
            }
            
            # 尝试解析内容
            content = response.text.strip()
            
            # 如果内容是base64编码，先解码
            try:
                # 检查是否是base64编码（通过尝试解码来判断）
                decoded_content = base64.b64decode(content).decode('utf-8')
                logger.debug("成功解码base64内容")
                content = decoded_content
            except Exception as e:
                logger.debug(f"内容不是base64编码��解码失败: {e}")
            
            # 尝试直接解析原始内容中的VLESS链接
            vless_links = []
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('vless://'):
                    vless_links.append(line)
            
            if vless_links:
                logger.info(f"找到 {len(vless_links)} 个VLESS链接")
                for link in vless_links:
                    try:
                        outbound = parse_vless_link(link)
                        outbound["tag"] = f"proxy_{len(config['outbounds'])}"
                        config["outbounds"].append(outbound)
                        logger.info(f"成功解析VLESS链接")
                    except Exception as e:
                        logger.warning(f"解析VLESS链接失败: {e}")
                        continue
                
                if not config["outbounds"]:
                    raise ValueError("未找到有效的VLESS链接")
            else:
                logger.warning("未找到VLESS链接，尝试其他格式...")
                return False
            
            # 保存配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            logger.info(f"配置已更新: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
        
    def start(self) -> bool:
        """启动V2Ray
        
        Returns:
            bool: 是否成功启动
        """
        try:
            if self.process:
                logger.warning("V2Ray已经在运行")
                return True
                
            # 如果配置文件不存在，尝试更新
            if not os.path.exists(self.config_path):
                if not self.update_config():
                    logger.error("无法获取V2Ray配置")
                    return False
            
            # 获取v2ray所在目录的绝对路径
            v2ray_dir = os.path.dirname(os.path.abspath(self.v2ray_path))
            config_path = os.path.abspath(self.config_path)
            
            logger.info(f"V2Ray工作目录: {v2ray_dir}")
            logger.info(f"V2Ray配置文件: {config_path}")
            logger.info(f"正在启动V2Ray: {self.v2ray_path}")
            
            # 使用subprocess.Popen启动v2ray进程，并实时捕获输出
            self.process = subprocess.Popen(
                [self.v2ray_path, "run", "-c", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=v2ray_dir,  # 设置工作目录为v2ray所在目录的绝对路径
                universal_newlines=True,  # 使用文本模式
                bufsize=1  # 行缓冲
            )
            
            # 等待几秒确保启动完成，同时读取输出
            start_time = time.time()
            while time.time() - start_time < 5:
                # 检查进程是否还在运行
                if self.process.poll() is not None:
                    error = self.process.stderr.read()
                    logger.error(f"V2Ray启动失败: {error}")
                    return False
                
                # 读取输出
                stdout_line = self.process.stdout.readline()
                if stdout_line:
                    logger.debug(f"V2Ray输出: {stdout_line.strip()}")
                stderr_line = self.process.stderr.readline()
                if stderr_line:
                    logger.error(f"V2Ray错误: {stderr_line.strip()}")
                
                time.sleep(0.1)
            
            # 最后检查进程状态
            if self.process.poll() is None:
                logger.info("V2Ray启动成功")
                return True
            else:
                error = self.process.stderr.read()
                logger.error(f"V2Ray启动失败: {error}")
                return False
                
        except Exception as e:
            logger.error(f"启动V2Ray时出错: {e}")
            if self.process:
                try:
                    self.process.kill()
                except:
                    pass
                self.process = None
            return False
            
    def stop(self) -> bool:
        """停止V2Ray
        
        Returns:
            bool: 是否成功停止
        """
        try:
            if not self.process:
                logger.warning("V2Ray未在运行")
                return True
                
            logger.info("正在停止V2Ray...")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
            logger.info("V2Ray已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止V2Ray时出错: {e}")
            if self.process:
                self.process.kill()
                self.process = None
            return False
            
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop() 

# 示例如何使用获取到的 v2ray 配置
if __name__ == "__main__":
    # 设置日志级别为DEBUG以查看详细信息
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试配置文件路径
    test_config = os.path.abspath("test_v2ray.json")
    logger.info(f"测试配置文件路径: {test_config}")
    
    # 测试链接
    test_link = "vless://9a52cb49-b2e1-4e61-8b0c-c0416918fac0@souwangpan.us.kg:443?encryption=none&security=tls&sni=souwangpan.us.kg&fp=randomized&type=ws&host=souwangpan.us.kg&path=%2F%3Fed%3D2560#edgetunnel"
    
    try:
        # 建基础配置
        config = {
            "log": {
                "loglevel": "debug",
                "access": "access.log",
                "error": "error.log"
            },
            "inbounds": [{
                "port": 1080,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {
                    "udp": True
                }
            }],
            "outbounds": []
        }
        
        # 解析VLESS链接并添加到配置中
        logger.info("正在解析VLESS链接...")
        outbound = parse_vless_link(test_link)
        outbound["tag"] = "proxy_0"
        config["outbounds"].append(outbound)
        
        # 保存配置文件
        logger.info(f"正在保存配置到: {test_config}")
        with open(test_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info("已创建测试配置文件")
        
        # 创建V2Ray控制器实例
        controller = V2RayController(config_path=test_config)
        
        logger.info("正在启动V2Ray...")
        if controller.start():
            logger.info("V2Ray启动成功!")
            logger.info("等待10秒后关闭...")
            time.sleep(10)
        else:
            logger.error("V2Ray启动失败!")
            
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        
    finally:
        # 停止V2Ray
        if 'controller' in locals():
            logger.info("正在停止V2Ray...")
            controller.stop()
        
        # 清理测试文件
        if os.path.exists(test_config):
            logger.info("正在清理测试文件...")
            os.remove(test_config)
            logger.info("测试文件已清理") 