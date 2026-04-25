"""
增强日志记录模块
提供结构化日志记录功能
"""
import logging
import os
from datetime import datetime

def setup_logger():
    """设置日志记录器"""
    # 创建logs目录
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志文件名
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 配置日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    
    return logging.getLogger(__name__)

# 全局日志记录器
logger = setup_logger()

def log_error(operation, error, user_id=None):
    """记录错误日志"""
    user_info = f" [用户ID: {user_id}]" if user_id else ""
    logger.error(f"{operation} 失生错误{user_info}: {str(error)}")

def log_info(operation, message, user_id=None):
    """记录信息日志"""
    user_info = f" [用户ID: {user_id}]" if user_id else ""
    logger.info(f"{operation}{user_info}: {message}")

def log_warning(operation, message, user_id=None):
    """记录警告日志"""
    user_info = f" [用户ID: {user_id}]" if user_id else ""
    logger.warning(f"{operation}{user_info}: {message}")