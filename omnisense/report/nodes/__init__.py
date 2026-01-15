#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generation Nodes

报告生成流程的各个节点
"""

from .base import BaseGenerationNode
from .template_selection import TemplateSelectionNode
from .document_layout import DocumentLayoutNode
from .word_budget import WordBudgetNode
from .chapter_generation import ChapterGenerationNode

__all__ = [
    'BaseGenerationNode',
    'TemplateSelectionNode',
    'DocumentLayoutNode',
    'WordBudgetNode',
    'ChapterGenerationNode',
]
