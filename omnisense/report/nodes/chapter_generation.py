#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter Generation Node

章节生成节点 - 使用LLM生成每个章节的内容（Document IR格式）
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from .base import BaseGenerationNode
from ..ir.schema import ChapterIR, BlockIR, BlockType, TextIR, ChartIR
from ..ir.validator import IRValidator


class ChapterGenerationNode(BaseGenerationNode):
    """章节生成节点"""

    def __init__(self, llm=None, config: Dict[str, Any] = None):
        super().__init__(llm, config)
        self.validator = IRValidator(strict_mode=False)
        self.max_retries = config.get('max_retries', 3) if config else 3
        self.concurrent_chapters = config.get('concurrent_chapters', 3) if config else 3

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成所有章节

        Args:
            context: 包含 document_layout, word_budget, data_summary 等

        Returns:
            更新后的context，添加 chapters (List[ChapterIR])
        """
        self.log_start()

        try:
            layout = context.get('document_layout', {})
            chapter_outline = layout.get('chapter_outline', [])
            word_budget = context.get('word_budget', {})
            data_summary = context.get('data_summary', {})
            analysis_results = context.get('analysis_results', {})

            # 并发生成章节
            chapters = await self._generate_chapters_concurrent(
                chapter_outline=chapter_outline,
                word_budget=word_budget,
                data_summary=data_summary,
                analysis_results=analysis_results,
                context=context
            )

            context['chapters'] = chapters

            self.log_complete(f"Generated {len(chapters)} chapters")
            return context

        except Exception as e:
            self.log_error(e)
            raise

    async def _generate_chapters_concurrent(
        self,
        chapter_outline: List[Dict[str, Any]],
        word_budget: Dict[str, int],
        data_summary: Dict[str, Any],
        analysis_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[ChapterIR]:
        """并发生成章节"""
        chapters = []

        # 分批并发生成
        for i in range(0, len(chapter_outline), self.concurrent_chapters):
            batch = chapter_outline[i:i + self.concurrent_chapters]

            tasks = [
                self._generate_single_chapter(
                    chapter_spec=spec,
                    word_budget=word_budget.get(spec['id'], 500),
                    data_summary=data_summary,
                    analysis_results=analysis_results,
                    context=context
                )
                for spec in batch
            ]

            batch_chapters = await asyncio.gather(*tasks, return_exceptions=True)

            for chapter in batch_chapters:
                if isinstance(chapter, Exception):
                    logger.error(f"Chapter generation failed: {chapter}")
                    continue
                if chapter:
                    chapters.append(chapter)

        return chapters

    async def _generate_single_chapter(
        self,
        chapter_spec: Dict[str, Any],
        word_budget: int,
        data_summary: Dict[str, Any],
        analysis_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[ChapterIR]:
        """生成单个章节"""
        chapter_id = chapter_spec['id']
        chapter_title = chapter_spec['title']

        logger.info(f"Generating chapter: {chapter_title} (budget: {word_budget} words)")

        for attempt in range(self.max_retries):
            try:
                # 构建提示
                prompt = self._build_chapter_prompt(
                    chapter_spec=chapter_spec,
                    word_budget=word_budget,
                    data_summary=data_summary,
                    analysis_results=analysis_results
                )

                # 调用LLM生成
                if self.llm:
                    response = await self.llm.apredict(prompt)
                else:
                    # 降级：生成简单章节
                    response = self._generate_fallback_chapter(chapter_spec)

                # 解析JSON
                chapter_json = self._parse_chapter_json(response)

                # 验证
                is_valid, errors = self.validator.validate_json_chapter(chapter_json)

                if not is_valid:
                    logger.warning(f"Chapter validation failed (attempt {attempt + 1}): {errors}")
                    if attempt < self.max_retries - 1:
                        # 尝试修复
                        chapter_json = self.validator.repair_chapter_json(chapter_json)
                        continue
                    else:
                        raise ValueError(f"Chapter validation failed: {errors}")

                # 创建ChapterIR
                chapter = ChapterIR(**chapter_json)
                logger.success(f"Generated chapter: {chapter_title}")
                return chapter

            except Exception as e:
                logger.error(f"Chapter generation error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败，返回空章节
                    return self._create_empty_chapter(chapter_spec)

        return None

    def _build_chapter_prompt(
        self,
        chapter_spec: Dict[str, Any],
        word_budget: int,
        data_summary: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> str:
        """构建章节生成提示"""
        chapter_title = chapter_spec['title']
        content_hint = chapter_spec.get('content_hint', '')

        prompt = f"""你是一个专业的数据分析报告撰写专家。请根据以下信息生成报告章节。

章节标题：{chapter_title}
字数要求：约{word_budget}字
内容提示：{content_hint}

数据摘要：
{json.dumps(data_summary, ensure_ascii=False, indent=2)}

分析结果：
{json.dumps(analysis_results, ensure_ascii=False, indent=2)}

要求：
1. 输出格式必须是JSON，符合以下schema：
{{
  "id": "chapter-x",
  "title": "章节标题",
  "level": 1,
  "content": [
    {{
      "type": "paragraph",
      "content": [{{"text": "段落文本", "marks": []}}]
    }},
    {{
      "type": "heading",
      "attrs": {{"level": 2}},
      "content": [{{"text": "小标题", "marks": []}}]
    }}
  ],
  "children": []
}}

2. 支持的block类型：paragraph, heading, list, table, chart
3. 内容要专业、数据驱动、有洞察力
4. 字数控制在{word_budget}字左右

请直接输出JSON，不要其他内容："""

        return prompt

    def _parse_chapter_json(self, response: str) -> Dict[str, Any]:
        """解析LLM响应中的JSON"""
        # 尝试提取JSON
        import re

        # 移除markdown代码块标记
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)

        # 尝试找到JSON对象
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                raise

        raise ValueError("No valid JSON found in response")

    def _generate_fallback_chapter(self, chapter_spec: Dict[str, Any]) -> str:
        """生成降级章节（当LLM不可用时）"""
        chapter_json = {
            "id": chapter_spec['id'],
            "title": chapter_spec['title'],
            "level": chapter_spec['level'],
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": f"本章节内容：{chapter_spec['title']}。",
                            "marks": []
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": "由于LLM不可用，此章节使用默认内容生成。",
                            "marks": []
                        }
                    ]
                }
            ],
            "children": []
        }
        return json.dumps(chapter_json, ensure_ascii=False)

    def _create_empty_chapter(self, chapter_spec: Dict[str, Any]) -> ChapterIR:
        """创建空章节（作为最后的降级方案）"""
        return ChapterIR(
            id=chapter_spec['id'],
            title=chapter_spec['title'],
            level=chapter_spec['level'],
            content=[
                BlockIR(
                    type=BlockType.PARAGRAPH,
                    content=[
                        TextIR(
                            text=f"章节 {chapter_spec['title']} 生成失败，请稍后重试。",
                            marks=[]
                        )
                    ]
                )
            ],
            children=[],
            metadata={'generation_failed': True}
        )
