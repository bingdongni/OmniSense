#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document IR (Intermediate Representation) 模块

提供报告生成的中间表示层，包括：
- Schema定义（块类型、标记类型）
- IR校验器
- IR装订器
"""

from .schema import (
    BlockType,
    MarkType,
    DocumentIR,
    ChapterIR,
    BlockIR,
    ChartIR,
)
from .validator import IRValidator
from .stitcher import IRStitcher

__all__ = [
    'BlockType',
    'MarkType',
    'DocumentIR',
    'ChapterIR',
    'BlockIR',
    'ChartIR',
    'IRValidator',
    'IRStitcher',
]
