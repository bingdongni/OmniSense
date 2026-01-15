#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Renderer

将Document IR渲染为Markdown格式
"""

from typing import List
from loguru import logger

from .base import BaseRenderer
from ..ir.schema import (
    DocumentIR,
    ChapterIR,
    BlockIR,
    BlockType,
    TextIR,
    ChartIR,
    MarkType,
)


class MarkdownRenderer(BaseRenderer):
    """Markdown渲染器"""

    def render(self, doc_ir: DocumentIR) -> str:
        """渲染为Markdown"""
        logger.info(f"Rendering document to Markdown: {doc_ir.title}")

        md_parts = []

        # 文档标题
        md_parts.append(f"# {doc_ir.title}\n")

        if doc_ir.subtitle:
            md_parts.append(f"**{doc_ir.subtitle}**\n")

        if doc_ir.authors:
            md_parts.append(f"*作者: {', '.join(doc_ir.authors)}*\n")

        if doc_ir.date:
            md_parts.append(f"*日期: {doc_ir.date}*\n")

        md_parts.append("\n---\n\n")

        # 目录
        if doc_ir.toc:
            md_parts.append(self._render_toc(doc_ir.toc))
            md_parts.append("\n---\n\n")

        # 章节内容
        for chapter in doc_ir.chapters:
            md_parts.append(self._render_chapter(chapter))
            md_parts.append("\n")

        return ''.join(md_parts)

    def _render_toc(self, toc: List[dict]) -> str:
        """渲染目录"""
        toc_lines = ["## 目录\n\n"]

        for item in toc:
            number = item.get('number', '')
            title = item.get('title', '')
            level = item.get('level', 1)
            indent = "  " * (level - 1)
            toc_lines.append(f"{indent}- {number}. {title}\n")

        return ''.join(toc_lines)

    def _render_chapter(self, chapter: ChapterIR, level: int = 2) -> str:
        """渲染章节"""
        md_parts = []

        # 章节标题
        heading_prefix = "#" * level
        md_parts.append(f"{heading_prefix} {chapter.title}\n\n")

        # 章节内容
        for block in chapter.content:
            md_parts.append(self._render_block(block))

        # 递归渲染子章节
        for child in chapter.children:
            md_parts.append(self._render_chapter(child, level + 1))

        return ''.join(md_parts)

    def _render_block(self, block: BlockIR) -> str:
        """渲染块"""
        if block.type == BlockType.PARAGRAPH:
            return self._render_paragraph(block)
        elif block.type == BlockType.HEADING:
            return self._render_heading(block)
        elif block.type == BlockType.LIST:
            return self._render_list(block)
        elif block.type == BlockType.TABLE:
            return self._render_table(block)
        elif block.type == BlockType.CHART:
            return self._render_chart(block)
        elif block.type == BlockType.CODE:
            return self._render_code(block)
        elif block.type == BlockType.QUOTE:
            return self._render_quote(block)
        elif block.type == BlockType.DIVIDER:
            return '\n---\n\n'
        else:
            return ''

    def _render_paragraph(self, block: BlockIR) -> str:
        """渲染段落"""
        content = self._render_inline_content(block.content)
        return f"{content}\n\n"

    def _render_heading(self, block: BlockIR) -> str:
        """渲染标题"""
        level = block.attrs.get('level', 3) if block.attrs else 3
        level = max(1, min(6, level))
        heading_prefix = "#" * level
        content = self._render_inline_content(block.content)
        return f"{heading_prefix} {content}\n\n"

    def _render_inline_content(self, content: List) -> str:
        """渲染内联内容"""
        if not content:
            return ''

        md_parts = []
        for item in content:
            if isinstance(item, TextIR):
                md_parts.append(self._render_text(item))
            elif isinstance(item, BlockIR):
                md_parts.append(self._render_block(item))

        return ''.join(md_parts)

    def _render_text(self, text: TextIR) -> str:
        """渲染文本"""
        content = text.text

        # 应用标记
        for mark in text.marks:
            if mark.type == MarkType.BOLD:
                content = f"**{content}**"
            elif mark.type == MarkType.ITALIC:
                content = f"*{content}*"
            elif mark.type == MarkType.CODE:
                content = f"`{content}`"
            elif mark.type == MarkType.LINK:
                href = mark.attrs.get('href', '#') if mark.attrs else '#'
                content = f"[{content}]({href})"
            elif mark.type == MarkType.HIGHLIGHT:
                content = f"=={content}=="

        return content

    def _render_list(self, block: BlockIR) -> str:
        """渲染列表"""
        ordered = block.attrs.get('ordered', False) if block.attrs else False
        items = []

        if block.content:
            for i, item in enumerate(block.content, 1):
                if isinstance(item, BlockIR):
                    item_content = self._render_inline_content(item.content)
                    prefix = f"{i}." if ordered else "-"
                    items.append(f"{prefix} {item_content}\n")

        return ''.join(items) + "\n"

    def _render_table(self, block: BlockIR) -> str:
        """渲染表格"""
        if not block.attrs or 'headers' not in block.attrs:
            return ''

        headers = block.attrs['headers']
        header_row = "| " + " | ".join(headers) + " |\n"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |\n"

        rows = []
        if block.content:
            for row_block in block.content:
                if isinstance(row_block, BlockIR) and row_block.content:
                    cells = [self._render_inline_content([cell]) if isinstance(cell, TextIR) else ''
                            for cell in row_block.content]
                    rows.append("| " + " | ".join(cells) + " |\n")

        return header_row + separator + ''.join(rows) + "\n"

    def _render_code(self, block: BlockIR) -> str:
        """渲染代码块"""
        content = self._render_inline_content(block.content)
        return f"```\n{content}\n```\n\n"

    def _render_quote(self, block: BlockIR) -> str:
        """渲染引用"""
        content = self._render_inline_content(block.content)
        lines = content.split('\n')
        quoted_lines = [f"> {line}" for line in lines if line.strip()]
        return '\n'.join(quoted_lines) + "\n\n"

    def _render_chart(self, block: BlockIR) -> str:
        """渲染图表（Markdown中用占位符表示）"""
        if not block.content:
            return ''

        chart_descriptions = []
        for item in block.content:
            if isinstance(item, ChartIR):
                chart_type = item.type
                chart_descriptions.append(f"*[图表: {chart_type}]*\n\n")

        return ''.join(chart_descriptions)

