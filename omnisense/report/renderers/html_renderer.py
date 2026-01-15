#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML Renderer

将Document IR渲染为HTML格式
"""

from typing import List, Dict, Any
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


class HTMLRenderer(BaseRenderer):
    """HTML渲染器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.include_toc = config.get('include_toc', True) if config else True
        self.include_charts = config.get('include_charts', True) if config else True
        self.theme = config.get('theme', 'default') if config else 'default'

    def render(self, doc_ir: DocumentIR) -> str:
        """渲染为HTML"""
        logger.info(f"Rendering document to HTML: {doc_ir.title}")

        html_parts = []

        # HTML头部
        html_parts.append(self._render_html_head(doc_ir))

        # 文档标题
        html_parts.append(self._render_document_header(doc_ir))

        # 目录
        if self.include_toc and doc_ir.toc:
            html_parts.append(self._render_toc(doc_ir.toc))

        # 章节内容
        for chapter in doc_ir.chapters:
            html_parts.append(self._render_chapter(chapter))

        # HTML尾部
        html_parts.append(self._render_html_footer())

        return '\n'.join(html_parts)

    def _render_html_head(self, doc_ir: DocumentIR) -> str:
        """渲染HTML头部"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc_ir.title}</title>
    <style>
        {self._get_css_styles()}
    </style>
    {self._get_chart_scripts() if self.include_charts else ''}
</head>
<body>
    <div class="container">"""

    def _get_css_styles(self) -> str:
        """获取CSS样式"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .document-header { text-align: center; padding: 40px 0; border-bottom: 2px solid #e0e0e0; margin-bottom: 40px; }
        .document-title { font-size: 2.5em; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
        .document-subtitle { font-size: 1.2em; color: #666; margin-bottom: 20px; }
        .document-meta { font-size: 0.9em; color: #999; }
        .toc { background: #f9f9f9; padding: 30px; border-radius: 8px; margin-bottom: 40px; }
        .toc-title { font-size: 1.5em; font-weight: 600; margin-bottom: 20px; color: #333; }
        .toc-list { list-style: none; }
        .toc-item { padding: 8px 0; border-bottom: 1px solid #e0e0e0; }
        .toc-item:last-child { border-bottom: none; }
        .toc-link { text-decoration: none; color: #0066cc; display: flex; justify-content: space-between; }
        .toc-link:hover { color: #0052a3; }
        .toc-number { font-weight: 600; margin-right: 10px; }
        .chapter { margin-bottom: 60px; }
        .chapter-title { font-size: 2em; font-weight: 600; color: #1a1a1a; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #0066cc; }
        h1 { font-size: 2em; margin: 30px 0 20px; }
        h2 { font-size: 1.75em; margin: 25px 0 15px; color: #333; }
        h3 { font-size: 1.5em; margin: 20px 0 10px; color: #444; }
        h4 { font-size: 1.25em; margin: 15px 0 10px; color: #555; }
        p { margin: 15px 0; text-align: justify; }
        ul, ol { margin: 15px 0; padding-left: 30px; }
        li { margin: 8px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border: 1px solid #ddd; }
        th { background: #f5f5f5; font-weight: 600; }
        tr:nth-child(even) { background: #fafafa; }
        .chart-container { margin: 30px 0; padding: 20px; background: #fafafa; border-radius: 8px; }
        .chart-title { font-size: 1.1em; font-weight: 600; margin-bottom: 15px; color: #333; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
        blockquote { border-left: 4px solid #0066cc; padding-left: 20px; margin: 20px 0; color: #666; font-style: italic; }
        .bold { font-weight: 600; }
        .italic { font-style: italic; }
        .highlight { background: #fff3cd; padding: 2px 4px; }
        @media print { body { background: white; } .container { box-shadow: none; } }
        """

    def _get_chart_scripts(self) -> str:
        """获取图表脚本"""
        return """
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <script>
        function renderChart(containerId, data, layout, config) {
            Plotly.newPlot(containerId, data, layout, config);
        }
    </script>"""

    def _render_document_header(self, doc_ir: DocumentIR) -> str:
        """渲染文档头部"""
        subtitle_html = f'<div class="document-subtitle">{doc_ir.subtitle}</div>' if doc_ir.subtitle else ''
        authors_html = f'<div class="document-meta">作者: {", ".join(doc_ir.authors)}</div>' if doc_ir.authors else ''
        date_html = f'<div class="document-meta">日期: {doc_ir.date}</div>' if doc_ir.date else ''

        return f"""
        <div class="document-header">
            <h1 class="document-title">{doc_ir.title}</h1>
            {subtitle_html}
            {authors_html}
            {date_html}
        </div>"""

    def _render_toc(self, toc: List[Dict[str, Any]]) -> str:
        """渲染目录"""
        toc_items = []
        for item in toc:
            number = item.get('number', '')
            title = item.get('title', '')
            chapter_id = item.get('id', '')
            toc_items.append(
                f'<li class="toc-item"><a href="#{chapter_id}" class="toc-link">'
                f'<span><span class="toc-number">{number}.</span>{title}</span></a></li>'
            )

        return f"""
        <div class="toc">
            <h2 class="toc-title">目录</h2>
            <ul class="toc-list">
                {''.join(toc_items)}
            </ul>
        </div>"""

    def _render_chapter(self, chapter: ChapterIR) -> str:
        """渲染章节"""
        chapter_id = chapter.id
        chapter_title = chapter.title

        content_html = ''.join([self._render_block(block) for block in chapter.content])

        # 递归渲染子章节
        children_html = ''.join([self._render_chapter(child) for child in chapter.children])

        return f"""
        <div class="chapter" id="{chapter_id}">
            <h2 class="chapter-title">{chapter_title}</h2>
            {content_html}
            {children_html}
        </div>"""

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
            return '<hr />'
        else:
            return ''

    def _render_paragraph(self, block: BlockIR) -> str:
        """渲染段落"""
        content = self._render_inline_content(block.content)
        return f'<p>{content}</p>'

    def _render_heading(self, block: BlockIR) -> str:
        """渲染标题"""
        level = block.attrs.get('level', 2) if block.attrs else 2
        level = max(1, min(6, level))  # 限制在1-6
        content = self._render_inline_content(block.content)
        anchor_id = block.attrs.get('id', '') if block.attrs else ''
        id_attr = f' id="{anchor_id}"' if anchor_id else ''
        return f'<h{level}{id_attr}>{content}</h{level}>'

    def _render_inline_content(self, content: List) -> str:
        """渲染内联内容"""
        if not content:
            return ''

        html_parts = []
        for item in content:
            if isinstance(item, TextIR):
                html_parts.append(self._render_text(item))
            elif isinstance(item, BlockIR):
                html_parts.append(self._render_block(item))

        return ''.join(html_parts)

    def _render_text(self, text: TextIR) -> str:
        """渲染文本"""
        content = text.text

        # 应用标记
        for mark in text.marks:
            if mark.type == MarkType.BOLD:
                content = f'<strong class="bold">{content}</strong>'
            elif mark.type == MarkType.ITALIC:
                content = f'<em class="italic">{content}</em>'
            elif mark.type == MarkType.CODE:
                content = f'<code>{content}</code>'
            elif mark.type == MarkType.LINK:
                href = mark.attrs.get('href', '#') if mark.attrs else '#'
                content = f'<a href="{href}">{content}</a>'
            elif mark.type == MarkType.HIGHLIGHT:
                content = f'<span class="highlight">{content}</span>'

        return content

    def _render_list(self, block: BlockIR) -> str:
        """渲染列表"""
        ordered = block.attrs.get('ordered', False) if block.attrs else False
        tag = 'ol' if ordered else 'ul'

        items = []
        if block.content:
            for item in block.content:
                if isinstance(item, BlockIR):
                    item_content = self._render_inline_content(item.content)
                    items.append(f'<li>{item_content}</li>')

        return f'<{tag}>{"".join(items)}</{tag}>'

    def _render_table(self, block: BlockIR) -> str:
        """渲染表格"""
        if not block.attrs or 'headers' not in block.attrs:
            return ''

        headers = block.attrs['headers']
        header_html = ''.join([f'<th>{h}</th>' for h in headers])

        rows_html = []
        if block.content:
            for row_block in block.content:
                if isinstance(row_block, BlockIR) and row_block.content:
                    cells = [self._render_inline_content([cell]) if isinstance(cell, TextIR) else ''
                            for cell in row_block.content]
                    rows_html.append(f'<tr>{"".join([f"<td>{c}</td>" for c in cells])}</tr>')

        return f'<table><thead><tr>{header_html}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'

    def _render_code(self, block: BlockIR) -> str:
        """渲染代码块"""
        content = self._render_inline_content(block.content)
        return f'<pre><code>{content}</code></pre>'

    def _render_quote(self, block: BlockIR) -> str:
        """渲染引用"""
        content = self._render_inline_content(block.content)
        return f'<blockquote>{content}</blockquote>'

    def _render_chart(self, block: BlockIR) -> str:
        """渲染图表"""
        if not self.include_charts or not block.content:
            return ''

        import json
        import uuid

        chart_id = f"chart-{uuid.uuid4().hex[:8]}"
        chart_html_parts = []

        for item in block.content:
            if isinstance(item, ChartIR):
                chart_html_parts.append(f'<div id="{chart_id}" class="chart-container"></div>')
                chart_html_parts.append('<script>')
                chart_html_parts.append(f'renderChart("{chart_id}", ')
                chart_html_parts.append(json.dumps(item.data))
                chart_html_parts.append(', ')
                chart_html_parts.append(json.dumps(item.layout or {}))
                chart_html_parts.append(', ')
                chart_html_parts.append(json.dumps(item.config or {}))
                chart_html_parts.append(');')
                chart_html_parts.append('</script>')

        return ''.join(chart_html_parts)

    def _render_html_footer(self) -> str:
        """渲染HTML尾部"""
        return """
    </div>
</body>
</html>"""

