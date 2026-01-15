#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Renderers

将Document IR渲染为不同格式（HTML, PDF, Markdown）
"""

from .base import BaseRenderer
from .html_renderer import HTMLRenderer
from .pdf_renderer import PDFRenderer
from .markdown_renderer import MarkdownRenderer

__all__ = [
    'BaseRenderer',
    'HTMLRenderer',
    'PDFRenderer',
    'MarkdownRenderer',
]
