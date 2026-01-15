#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Generation Node

报告生成节点的基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger


class BaseGenerationNode(ABC):
    """生成节点基类"""

    def __init__(self, llm=None, config: Optional[Dict[str, Any]] = None):
        """
        初始化节点

        Args:
            llm: LLM实例
            config: 节点配置
        """
        self.llm = llm
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理节点逻辑

        Args:
            context: 上下文数据

        Returns:
            更新后的上下文
        """
        pass

    def log_start(self):
        """记录节点开始"""
        logger.info(f"[{self.name}] Starting...")

    def log_complete(self, result_summary: str = ""):
        """记录节点完成"""
        logger.success(f"[{self.name}] Completed. {result_summary}")

    def log_error(self, error: Exception):
        """记录节点错误"""
        logger.error(f"[{self.name}] Error: {error}")
