#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Layout Node

文档布局节点 - 设计报告的整体结构、标题、目录等
"""

from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from .base import BaseGenerationNode


class DocumentLayoutNode(BaseGenerationNode):
    """文档布局节点"""

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        设计文档布局

        Args:
            context: 包含 template, query, data_summary 等

        Returns:
            更新后的context，添加 document_layout
        """
        self.log_start()

        try:
            template = context.get('template')
            query = context.get('query', '')
            data_summary = context.get('data_summary', {})

            # 生成文档标题
            title = await self._generate_title(query, data_summary, template)

            # 生成副标题
            subtitle = await self._generate_subtitle(data_summary)

            # 生成作者信息
            authors = context.get('authors', ['OmniSense AI'])

            # 生成日期
            date = datetime.now().strftime("%Y-%m-%d")

            # 构建章节大纲
            chapter_outline = self._build_chapter_outline(template)

            # 文档布局
            layout = {
                'title': title,
                'subtitle': subtitle,
                'authors': authors,
                'date': date,
                'chapter_outline': chapter_outline,
                'total_chapters': len(chapter_outline),
            }

            context['document_layout'] = layout

            self.log_complete(f"Title: {title}, Chapters: {len(chapter_outline)}")
            return context

        except Exception as e:
            self.log_error(e)
            raise

    async def _generate_title(
        self,
        query: str,
        data_summary: Dict[str, Any],
        template
    ) -> str:
        """生成文档标题"""
        if self.llm:
            prompt = f"""根据用户需求和数据摘要，生成一个专业的报告标题。

用户需求：{query}

数据摘要：
- 数据来源：{data_summary.get('platforms', [])}
- 数据量：{data_summary.get('total_items', 0)}
- 时间范围：{data_summary.get('time_range', '')}

要求：
1. 标题要简洁专业，10-30字
2. 体现报告的核心内容
3. 只返回标题文本，不要其他内容

标题："""

            try:
                # 使用 ainvoke 替代 apredict
                if hasattr(self.llm, 'ainvoke'):
                    response = await self.llm.ainvoke(prompt)
                    title = response.content if hasattr(response, 'content') else str(response)
                elif hasattr(self.llm, 'agenerate'):
                    response = await self.llm.agenerate([prompt])
                    title = response.generations[0][0].text
                else:
                    # 同步fallback
                    title = self.llm.invoke(prompt)
                    title = title.content if hasattr(title, 'content') else str(title)

                title = title.strip().strip('"\'')
                return title[:100]  # 限制长度
            except Exception as e:
                logger.warning(f"LLM title generation failed: {e}")

        # 降级：基于模板和查询生成
        template_title = template.title if template else "数据分析报告"
        return f"{template_title} - {query[:30]}"

    async def _generate_subtitle(self, data_summary: Dict[str, Any]) -> str:
        """生成副标题"""
        platforms = data_summary.get('platforms', [])
        time_range = data_summary.get('time_range', '')

        parts = []
        if platforms:
            parts.append(f"基于{', '.join(platforms[:3])}等平台")
        if time_range:
            parts.append(f"时间范围：{time_range}")

        return ' | '.join(parts) if parts else None

    def _build_chapter_outline(self, template) -> List[Dict[str, Any]]:
        """构建章节大纲"""
        if not template:
            return []

        outline = []

        def process_sections(sections, parent_number=""):
            for i, section in enumerate(sections, 1):
                number = f"{parent_number}{i}" if parent_number else str(i)
                outline.append({
                    'id': f"chapter-{number.replace('.', '-')}",
                    'number': number,
                    'title': section.title,
                    'level': section.level,
                    'content_hint': section.content[:100] if section.content else "",
                })

                if section.children:
                    process_sections(section.children, f"{number}.")

        process_sections(template.sections)
        return outline
