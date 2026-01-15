#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OmniSense Report Generation System

完整的报告生成系统，包括：
- Document IR中间表示
- 模板管理
- 多节点生成流程
- 多格式渲染（HTML/PDF/Markdown）
"""

from .engine import ReportEngine
from .template_manager import TemplateManager
from .ir import DocumentIR, ChapterIR, BlockIR, ChartIR
from .renderers import HTMLRenderer, PDFRenderer, MarkdownRenderer

__all__ = [
    'ReportEngine',
    'TemplateManager',
    'DocumentIR',
    'ChapterIR',
    'BlockIR',
    'ChartIR',
    'HTMLRenderer',
    'PDFRenderer',
    'MarkdownRenderer',
]
