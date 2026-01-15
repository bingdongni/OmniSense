#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Renderer

渲染器基类
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from loguru import logger

from ..ir.schema import DocumentIR


class BaseRenderer(ABC):
    """渲染器基类"""

    def __init__(self, config: Optional[dict] = None):
        """
        初始化渲染器

        Args:
            config: 渲染器配置
        """
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def render(self, doc_ir: DocumentIR) -> str:
        """
        渲染文档

        Args:
            doc_ir: 文档IR

        Returns:
            渲染后的内容（字符串）
        """
        pass

    def render_to_file(self, doc_ir: DocumentIR, output_path: str) -> str:
        """
        渲染并保存到文件

        Args:
            doc_ir: 文档IR
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        logger.info(f"[{self.name}] Rendering to {output_path}")

        try:
            content = self.render(doc_ir)

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.success(f"[{self.name}] Rendered to {output_path}")
            return str(output_file)

        except Exception as e:
            logger.error(f"[{self.name}] Render failed: {e}")
            raise
