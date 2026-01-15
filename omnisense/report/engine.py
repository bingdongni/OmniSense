#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Engine

报告生成引擎 - 整合所有节点和渲染器
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger

from .template_manager import TemplateManager
from .nodes import (
    TemplateSelectionNode,
    DocumentLayoutNode,
    WordBudgetNode,
    ChapterGenerationNode,
)
from .ir import DocumentIR, IRStitcher, IRValidator
from .renderers import HTMLRenderer, PDFRenderer, MarkdownRenderer


class ReportEngine:
    """报告生成引擎"""

    def __init__(
        self,
        llm=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化报告引擎

        Args:
            llm: LLM实例（用于章节生成）
            config: 引擎配置
        """
        self.llm = llm
        self.config = config or {}

        # 初始化组件
        self.template_manager = TemplateManager()
        self.stitcher = IRStitcher()
        self.validator = IRValidator()

        # 初始化节点
        self._init_nodes()

        # 初始化渲染器
        self._init_renderers()

        logger.info("ReportEngine initialized")

    def _init_nodes(self):
        """初始化生成节点"""
        node_config = self.config.get('node_config', {})

        self.template_selection_node = TemplateSelectionNode(
            llm=self.llm,
            config=node_config.get('template_selection', {})
        )

        self.document_layout_node = DocumentLayoutNode(
            llm=self.llm,
            config=node_config.get('document_layout', {})
        )

        self.word_budget_node = WordBudgetNode(
            llm=self.llm,
            config=node_config.get('word_budget', {})
        )

        self.chapter_generation_node = ChapterGenerationNode(
            llm=self.llm,
            config=node_config.get('chapter_generation', {})
        )

    def _init_renderers(self):
        """初始化渲染器"""
        renderer_config = self.config.get('renderer_config', {})

        self.html_renderer = HTMLRenderer(
            config=renderer_config.get('html', {})
        )

        self.pdf_renderer = PDFRenderer(
            config=renderer_config.get('pdf', {})
        )

        self.markdown_renderer = MarkdownRenderer(
            config=renderer_config.get('markdown', {})
        )

    async def generate_report(
        self,
        query: str,
        data_summary: Dict[str, Any],
        analysis_results: Optional[Dict[str, Any]] = None,
        template_name: Optional[str] = None,
        target_words: int = 5000,
        output_format: str = 'html',
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成完整报告

        Args:
            query: 用户查询/需求
            data_summary: 数据摘要
            analysis_results: 分析结果
            template_name: 指定模板名称（可选）
            target_words: 目标字数
            output_format: 输出格式 (html/pdf/markdown)
            output_path: 输出文件路径（可选）
            **kwargs: 其他参数

        Returns:
            包含document_ir和output_path的字典
        """
        logger.info(f"Starting report generation: {query}")

        try:
            # 构建上下文
            context = {
                'query': query,
                'data_summary': data_summary,
                'analysis_results': analysis_results or {},
                'target_words': target_words,
                **kwargs
            }

            # 执行生成流程
            context = await self._execute_generation_pipeline(context, template_name)

            # 装订文档
            doc_ir = self._stitch_document(context)

            # 渲染输出
            output_file = self._render_output(doc_ir, output_format, output_path)

            logger.success(f"Report generation completed: {output_file}")

            return {
                'document_ir': doc_ir,
                'output_path': output_file,
                'format': output_format,
            }

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise

    async def _execute_generation_pipeline(
        self,
        context: Dict[str, Any],
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行生成流程"""
        logger.info("Executing generation pipeline")

        # 节点1: 模板选择
        if template_name:
            context['template_name'] = template_name
            context['template'] = self.template_manager.get_template(template_name)
        else:
            context = await self.template_selection_node.process(context)

        # 节点2: 文档布局
        context = await self.document_layout_node.process(context)

        # 节点3: 字数预算
        context = await self.word_budget_node.process(context)

        # 节点4: 章节生成
        context = await self.chapter_generation_node.process(context)

        return context

    def _stitch_document(self, context: Dict[str, Any]) -> DocumentIR:
        """装订文档"""
        logger.info("Stitching document")

        layout = context.get('document_layout', {})
        chapters = context.get('chapters', [])

        doc_ir = self.stitcher.stitch_document(
            chapters=chapters,
            title=layout.get('title', 'Untitled Report'),
            subtitle=layout.get('subtitle'),
            authors=layout.get('authors', ['OmniSense AI']),
            template=context.get('template_name', 'default'),
            metadata=context.get('metadata', {})
        )

        # 验证文档
        is_valid, errors, warnings = self.validator.validate_document(doc_ir)
        if not is_valid:
            logger.warning(f"Document validation errors: {errors}")
        if warnings:
            logger.warning(f"Document validation warnings: {warnings}")

        return doc_ir

    def _render_output(
        self,
        doc_ir: DocumentIR,
        output_format: str,
        output_path: Optional[str] = None
    ) -> str:
        """渲染输出"""
        logger.info(f"Rendering output: {output_format}")

        # 生成默认输出路径
        if not output_path:
            output_dir = Path('reports')
            output_dir.mkdir(exist_ok=True)

            safe_title = "".join(c for c in doc_ir.title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]

            ext = {'html': '.html', 'pdf': '.pdf', 'markdown': '.md'}.get(output_format, '.html')
            output_path = str(output_dir / f"{safe_title}{ext}")

        # 选择渲染器
        if output_format == 'html':
            return self.html_renderer.render_to_file(doc_ir, output_path)
        elif output_format == 'pdf':
            return self.pdf_renderer.render_to_file(doc_ir, output_path)
        elif output_format == 'markdown':
            return self.markdown_renderer.render_to_file(doc_ir, output_path)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
