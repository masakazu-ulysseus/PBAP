"""
Logging utility using Loguru

Features:
- File rotation: 5MB max size, 3 generations
- operation.log: INFO, WARNING logs
- error.log: ERROR logs with traceback

Usage:
    from utils.logger import logger

    logger.info("操作ログ")
    logger.warning("警告ログ")
    logger.error("エラーログ")
"""

import sys
from pathlib import Path
from loguru import logger

# ログディレクトリの作成
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# デフォルトのstderr出力を削除
logger.remove()

# コンソール出力（INFO以上）
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# 操作ログファイル（INFO, WARNING）
logger.add(
    LOG_DIR / "operation.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="5 MB",
    retention=3,
    compression="zip",
    encoding="utf-8",
    filter=lambda record: record["level"].name in ["INFO", "SUCCESS", "WARNING"],
)

# エラーログファイル（ERROR以上）
logger.add(
    LOG_DIR / "error.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    rotation="5 MB",
    retention=3,
    compression="zip",
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
)
