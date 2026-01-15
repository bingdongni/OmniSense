"""
Logging and monitoring system for OmniSense
Provides structured logging with file rotation and console output
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger
from omnisense.config import config


class Logger:
    """Centralized logger for OmniSense"""

    def __init__(self):
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with file and console handlers"""
        # Remove default handler
        logger.remove()

        # Console handler with color
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            level=config.log_level,
            colorize=True,
        )

        # File handler with rotation
        log_file = Path(config.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_file),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level=config.log_level,
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
        )

        # Error file handler
        error_log_file = log_file.parent / f"{log_file.stem}_error.log"
        logger.add(
            str(error_log_file),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation="50 MB",
            retention="60 days",
            compression="zip",
            encoding="utf-8",
        )

    @staticmethod
    def get_logger(name: Optional[str] = None):
        """Get logger instance"""
        if name:
            return logger.bind(name=name)
        return logger


# Global logger instance
log = Logger().get_logger("omnisense")


def get_logger(name: str):
    """Get a named logger"""
    return Logger().get_logger(name)
