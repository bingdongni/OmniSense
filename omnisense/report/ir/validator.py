#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document IR Validator

验证Document IR的结构和内容是否符合规范
"""

from typing import List, Dict, Any, Tuple
from loguru import logger

from .schema import (
    DocumentIR,
    ChapterIR,
    BlockIR,
    ChartIR,
    BlockType,
    TextIR,
)


class ValidationError(Exception):
    """验证错误"""
    pass


class IRValidator:
    """IR验证器"""

    def __init__(self, strict_mode: bool = False):
        """
        初始化验证器

        Args:
            strict_mode: 严格模式，启用所有验证规则
        """
        self.strict_mode = strict_mode
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_document(self, doc_ir: DocumentIR) -> Tuple[bool, List[str], List[str]]:
        """
        验证完整文档

        Args:
            doc_ir: 文档IR

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        self.errors = []
        self.warnings = []

        # 基本验证
        if not doc_ir.title:
            self.errors.append("Document title is required")

        if not doc_ir.chapters:
            self.errors.append("Document must have at least one chapter")

        # 验证章节
        for i, chapter in enumerate(doc_ir.chapters):
            self._validate_chapter(chapter, f"Chapter {i + 1}")

        # 验证图表
        charts = doc_ir.get_all_charts()
        for i, chart in enumerate(charts):
            self._validate_chart(chart, f"Chart {i + 1}")

        # 验证字数（可选）
        if self.strict_mode:
            total_words = doc_ir.count_total_words()
            if total_words < 100:
                self.warnings.append(f"Document too short ({total_words} words)")
            elif total_words > 50000:
                self.warnings.append(f"Document very long ({total_words} words)")

        # 验证目录
        if doc_ir.toc is None:
            self.warnings.append("Document TOC not generated, call generate_toc()")

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_chapter(self, chapter: ChapterIR, context: str):
        """验证章节"""
        # 验证ID格式
        if not chapter.id.startswith('chapter-'):
            self.errors.append(f"{context}: Invalid chapter ID format: {chapter.id}")

        # 验证标题
        if not chapter.title or not chapter.title.strip():
            self.errors.append(f"{context}: Chapter title is empty")

        # 验证层级
        if chapter.level < 1 or chapter.level > 3:
            self.errors.append(f"{context}: Invalid chapter level: {chapter.level}")

        # 验证内容
        if not chapter.content and not chapter.children:
            self.warnings.append(f"{context}: Chapter has no content or children")

        # 验证块
        for i, block in enumerate(chapter.content):
            self._validate_block(block, f"{context}, Block {i + 1}")

        # 递归验证子章节
        for i, child in enumerate(chapter.children):
            self._validate_chapter(child, f"{context}, Subchapter {i + 1}")

    def _validate_block(self, block: BlockIR, context: str):
        """验证块"""
        # 根据块类型验证属性
        if block.type == BlockType.HEADING:
            if not block.attrs or 'level' not in block.attrs:
                self.errors.append(f"{context}: Heading block missing 'level' attribute")
            elif not (1 <= block.attrs['level'] <= 6):
                self.errors.append(
                    f"{context}: Invalid heading level: {block.attrs['level']}"
                )

        elif block.type == BlockType.LIST:
            if not block.attrs or 'ordered' not in block.attrs:
                self.errors.append(f"{context}: List block missing 'ordered' attribute")

        elif block.type == BlockType.TABLE:
            if not block.attrs or 'headers' not in block.attrs:
                self.errors.append(f"{context}: Table block missing 'headers' attribute")

        elif block.type == BlockType.CHART:
            # 图表块应该在content中包含ChartIR
            if not block.content:
                self.errors.append(f"{context}: Chart block has no content")
            else:
                for item in block.content:
                    if isinstance(item, ChartIR):
                        self._validate_chart(item, context)

        # 验证内容
        if block.content:
            for i, item in enumerate(block.content):
                if isinstance(item, BlockIR):
                    self._validate_block(item, f"{context}, Nested {i + 1}")
                elif isinstance(item, TextIR):
                    self._validate_text(item, f"{context}, Text {i + 1}")

    def _validate_text(self, text: TextIR, context: str):
        """验证文本节点"""
        if not text.text:
            self.warnings.append(f"{context}: Empty text node")

        # 验证标记
        for mark in text.marks:
            if mark.type.value not in ['bold', 'italic', 'code', 'link', 'highlight']:
                self.errors.append(f"{context}: Invalid mark type: {mark.type}")

            # 链接标记必须有href属性
            if mark.type.value == 'link':
                if not mark.attrs or 'href' not in mark.attrs:
                    self.errors.append(f"{context}: Link mark missing 'href' attribute")

    def _validate_chart(self, chart: ChartIR, context: str):
        """验证图表"""
        # 验证类型
        valid_types = [
            'bar', 'line', 'pie', 'scatter', 'heatmap',
            'box', 'histogram', 'radar', 'funnel', 'sankey', 'treemap'
        ]
        if chart.type not in valid_types:
            self.errors.append(
                f"{context}: Invalid chart type: {chart.type}. "
                f"Valid types: {valid_types}"
            )

        # 验证数据
        if not chart.data:
            self.errors.append(f"{context}: Chart has no data")
        else:
            # 检查基本数据结构
            has_data = (
                'x' in chart.data or
                'y' in chart.data or
                'values' in chart.data or
                'labels' in chart.data
            )
            if not has_data:
                self.errors.append(
                    f"{context}: Chart data missing required fields "
                    "(x, y, values, or labels)"
                )

            # 特定图表类型的验证
            if chart.type == 'pie':
                if 'labels' not in chart.data or 'values' not in chart.data:
                    self.errors.append(
                        f"{context}: Pie chart must have 'labels' and 'values'"
                    )

            elif chart.type in ['bar', 'line']:
                if 'x' not in chart.data or 'y' not in chart.data:
                    self.errors.append(
                        f"{context}: {chart.type.capitalize()} chart must have 'x' and 'y'"
                    )

            elif chart.type == 'scatter':
                if 'x' not in chart.data or 'y' not in chart.data:
                    self.errors.append(
                        f"{context}: Scatter chart must have 'x' and 'y'"
                    )

    def validate_json_chapter(self, chapter_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证JSON格式的章节（用于章节生成节点）

        Args:
            chapter_json: 章节JSON数据

        Returns:
            (是否通过, 错误列表)
        """
        errors = []

        # 必需字段
        required_fields = ['id', 'title', 'content']
        for field in required_fields:
            if field not in chapter_json:
                errors.append(f"Missing required field: {field}")

        # 验证ID格式
        if 'id' in chapter_json and not chapter_json['id'].startswith('chapter-'):
            errors.append(f"Invalid chapter ID format: {chapter_json['id']}")

        # 验证标题
        if 'title' in chapter_json:
            if not chapter_json['title'] or not str(chapter_json['title']).strip():
                errors.append("Chapter title is empty")

        # 验证内容为列表
        if 'content' in chapter_json:
            if not isinstance(chapter_json['content'], list):
                errors.append("Chapter content must be a list")

        # 尝试用Pydantic验证
        if not errors:
            try:
                ChapterIR(**chapter_json)
            except Exception as e:
                errors.append(f"Pydantic validation failed: {str(e)}")

        return len(errors) == 0, errors

    def repair_chapter_json(self, chapter_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        修复章节JSON（尝试自动修复常见问题）

        Args:
            chapter_json: 章节JSON数据

        Returns:
            修复后的章节JSON
        """
        repaired = chapter_json.copy()

        # 修复ID
        if 'id' not in repaired or not repaired['id']:
            repaired['id'] = 'chapter-auto'
        elif not repaired['id'].startswith('chapter-'):
            repaired['id'] = f"chapter-{repaired['id']}"

        # 修复标题
        if 'title' not in repaired or not repaired['title']:
            repaired['title'] = 'Untitled Chapter'

        # 修复层级
        if 'level' not in repaired:
            repaired['level'] = 1
        elif repaired['level'] < 1:
            repaired['level'] = 1
        elif repaired['level'] > 3:
            repaired['level'] = 3

        # 修复内容
        if 'content' not in repaired:
            repaired['content'] = []
        elif not isinstance(repaired['content'], list):
            repaired['content'] = []

        # 修复子章节
        if 'children' in repaired and not isinstance(repaired['children'], list):
            repaired['children'] = []

        return repaired

    def log_validation_results(self):
        """记录验证结果"""
        if self.errors:
            logger.error(f"Validation failed with {len(self.errors)} errors:")
            for error in self.errors:
                logger.error(f"  - {error}")

        if self.warnings:
            logger.warning(f"Validation has {len(self.warnings)} warnings:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        if not self.errors and not self.warnings:
            logger.success("Validation passed with no errors or warnings")
