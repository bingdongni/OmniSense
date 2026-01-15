#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template Selection Node

模板选择节点 - 根据用户需求和数据特征选择最合适的报告模板
"""

from typing import Dict, Any
from loguru import logger

from .base import BaseGenerationNode
from ..template_manager import TemplateManager


class TemplateSelectionNode(BaseGenerationNode):
    """模板选择节点"""

    def __init__(self, llm=None, config: Dict[str, Any] = None):
        super().__init__(llm, config)
        self.template_manager = TemplateManager()

    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        选择合适的模板

        Args:
            context: 包含 query, data_summary 等信息

        Returns:
            更新后的context，添加 template_name, template
        """
        self.log_start()

        query = context.get('query', '')
        data_summary = context.get('data_summary', {})
        use_llm = context.get('use_llm_selection', False)

        try:
            if use_llm and self.llm:
                # 使用LLM智能选择
                template_name, reason = await self.template_manager.select_template_with_llm(
                    query=query,
                    data_summary=data_summary,
                    llm=self.llm
                )
                logger.info(f"LLM selected template: {template_name}, reason: {reason}")
            else:
                # 基于规则选择
                template_name = self.template_manager.select_template(
                    query=query,
                    data_summary=data_summary
                )
                reason = "基于关键词匹配"
                logger.info(f"Rule-based selected template: {template_name}")

            # 获取模板
            template = self.template_manager.get_template(template_name)
            if not template:
                raise ValueError(f"Template not found: {template_name}")

            # 更新上下文
            context['template_name'] = template_name
            context['template'] = template
            context['selection_reason'] = reason

            self.log_complete(f"Selected: {template_name}")
            return context

        except Exception as e:
            self.log_error(e)
            # 降级到默认模板
            logger.warning("Falling back to default template")
            template = self.template_manager.get_template('default')
            context['template_name'] = 'default'
            context['template'] = template
            context['selection_reason'] = '选择失败，使用默认模板'
            return context
