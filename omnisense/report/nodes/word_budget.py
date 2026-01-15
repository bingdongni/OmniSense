#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word Budget Node

字数预算节点 - 为每个章节分配合理的字数预算
"""

from typing import Dict, Any, List
from loguru import logger

from .base import BaseGenerationNode


class WordBudgetNode(BaseGenerationNode):
    """字数预算节点"""

    def __init__(self, llm=None, config: Dict[str, Any] = None):
        super().__init__(llm, config)
        self.default_total_words = config.get('default_total_words', 5000) if config else 5000
        self.min_chapter_words = config.get('min_chapter_words', 200) if config else 200
        self.max_chapter_words = config.get('max_chapter_words', 2000) if config else 2000

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分配字数预算

        Args:
            context: 包含 document_layout, data_summary 等

        Returns:
            更新后的context，添加 word_budget
        """
        self.log_start()

        try:
            layout = context.get('document_layout', {})
            chapter_outline = layout.get('chapter_outline', [])

            # 获取目标总字数
            target_words = context.get('target_words', self.default_total_words)

            # 分配字数
            word_budget = self._allocate_word_budget(
                chapter_outline,
                target_words
            )

            context['word_budget'] = word_budget
            context['target_total_words'] = target_words

            self.log_complete(f"Total: {target_words} words, Chapters: {len(word_budget)}")
            return context

        except Exception as e:
            self.log_error(e)
            raise

    def _allocate_word_budget(
        self,
        chapter_outline: List[Dict[str, Any]],
        total_words: int
    ) -> Dict[str, int]:
        """
        分配字数预算

        Args:
            chapter_outline: 章节大纲
            total_words: 总字数

        Returns:
            章节ID到字数的映射
        """
        budget = {}

        # 计算章节权重
        chapter_weights = self._calculate_chapter_weights(chapter_outline)

        # 按权重分配
        total_weight = sum(chapter_weights.values())

        for chapter_id, weight in chapter_weights.items():
            allocated = int((weight / total_weight) * total_words)
            # 限制在合理范围
            allocated = max(self.min_chapter_words, min(allocated, self.max_chapter_words))
            budget[chapter_id] = allocated

        return budget

    def _calculate_chapter_weights(
        self,
        chapter_outline: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        计算章节权重

        Args:
            chapter_outline: 章节大纲

        Returns:
            章节ID到权重的映射
        """
        weights = {}

        for chapter in chapter_outline:
            chapter_id = chapter['id']
            level = chapter['level']

            # 基础权重：层级越高权重越大
            base_weight = 1.0
            if level == 1:
                base_weight = 1.5
            elif level == 2:
                base_weight = 1.0
            else:
                base_weight = 0.7

            # 特殊章节调整
            title = chapter['title'].lower()
            if any(keyword in title for keyword in ['执行摘要', '摘要', 'summary', 'executive']):
                base_weight *= 0.8  # 摘要相对简短
            elif any(keyword in title for keyword in ['分析', 'analysis', '结果', 'results']):
                base_weight *= 1.3  # 分析章节更详细
            elif any(keyword in title for keyword in ['附录', 'appendix', '参考', 'reference']):
                base_weight *= 0.6  # 附录相对简短

            weights[chapter_id] = base_weight

        return weights
