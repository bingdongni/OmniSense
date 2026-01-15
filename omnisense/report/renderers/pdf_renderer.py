#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Renderer

使用WeasyPrint将HTML转换为PDF
"""

from pathlib import Path
from typing import Optional
from loguru import logger

from .base import BaseRenderer
from .html_renderer import HTMLRenderer
from ..ir.schema import DocumentIR


class PDFRenderer(BaseRenderer):
    """PDF渲染器"""

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.html_renderer = HTMLRenderer(config)

    def render(self, doc_ir: DocumentIR) -> str:
        """
        渲染为PDF（返回HTML，实际PDF生成在render_to_file中）

        Args:
            doc_ir: 文档IR

        Returns:
            HTML内容
        """
        return self.html_renderer.render(doc_ir)

    def render_to_file(self, doc_ir: DocumentIR, output_path: str) -> str:
        """
        渲染并保存为PDF文件

        Args:
            doc_ir: 文档IR
            output_path: 输出PDF文件路径

        Returns:
            输出文件路径
        """
        logger.info(f"[{self.name}] Rendering to PDF: {output_path}")

        try:
            # 首先生成HTML
            html_content = self.html_renderer.render(doc_ir)

            # 使用WeasyPrint转换为PDF
            try:
                from weasyprint import HTML, CSS
            except ImportError:
                logger.error("WeasyPrint not installed. Install with: pip install weasyprint")
                raise ImportError(
                    "WeasyPrint is required for PDF generation. "
                    "Install it with: pip install weasyprint"
                )

            # 创建输出目录
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 生成PDF
            html_doc = HTML(string=html_content)

            # 添加PDF特定的CSS
            pdf_css = CSS(string=self._get_pdf_css())

            html_doc.write_pdf(
                output_path,
                stylesheets=[pdf_css]
            )

            logger.success(f"[{self.name}] PDF generated: {output_path}")
            return str(output_file)

        except Exception as e:
            logger.error(f"[{self.name}] PDF generation failed: {e}")
            raise

    def _get_pdf_css(self) -> str:
        """获取PDF特定的CSS样式"""
        return """
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            background: white !important;
        }

        .container {
            box-shadow: none !important;
        }

        .chapter {
            page-break-before: always;
        }

        .chapter:first-of-type {
            page-break-before: avoid;
        }

        h1, h2, h3 {
            page-break-after: avoid;
        }

        table {
            page-break-inside: avoid;
        }

        .chart-container {
            page-break-inside: avoid;
        }
        """
