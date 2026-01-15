"""
Core OmniSense class - Main entry point for the system
整合所有模块的核心类
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import asyncio

from omnisense.config import config
from omnisense.utils.logger import get_logger
from omnisense.spider.manager import SpiderManager
from omnisense.anti_crawl.manager import AntiCrawlManager
from omnisense.matcher.manager import MatcherManager
from omnisense.interaction.manager import InteractionManager
from omnisense.agents.manager import AgentManager
from omnisense.analysis.engine import AnalysisEngine
from omnisense.storage.database import DatabaseManager
from omnisense.visualization.renderer import VisualizationRenderer

logger = get_logger(__name__)


class OmniSense:
    """
    OmniSense主类 - 全域数据智能洞察平台核心接口

    Example:
        >>> omni = OmniSense()
        >>> result = omni.collect(platform="douyin", keyword="AI编程", max_count=100)
        >>> analysis = omni.analyze(data=result, agents=["analyst", "creator"])
        >>> omni.generate_report(analysis=analysis, format="pdf", output="report.pdf")
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize OmniSense system

        Args:
            config_file: Path to configuration file (optional)
        """
        logger.info("Initializing OmniSense system...")

        if config_file:
            from omnisense.config import Config
            global config
            config = Config.from_file(config_file)

        # Initialize managers
        self.db = DatabaseManager()
        self.spider_manager = SpiderManager()
        self.anti_crawl_manager = AntiCrawlManager()
        self.matcher_manager = MatcherManager()
        self.interaction_manager = InteractionManager()
        self.agent_manager = AgentManager()
        self.analysis_engine = AnalysisEngine()
        self.viz_renderer = VisualizationRenderer()

        logger.info("OmniSense system initialized successfully")

    async def collect_async(
        self,
        platform: str,
        keyword: Optional[str] = None,
        user_id: Optional[str] = None,
        url: Optional[str] = None,
        max_count: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步采集平台数据

        Args:
            platform: 平台名称 (douyin, xiaohongshu, weibo, etc.)
            keyword: 搜索关键词
            user_id: 用户ID
            url: 直接URL
            max_count: 最大采集数量
            filters: 过滤条件
            **kwargs: 平台特定参数

        Returns:
            采集结果字典
        """
        logger.info(f"Starting data collection for platform: {platform}")

        try:
            # Get platform spider
            spider = self.spider_manager.get_spider(platform)

            # Apply anti-crawl measures
            anti_crawl = self.anti_crawl_manager.get_handler(platform)
            await anti_crawl.setup()

            # Collect data
            raw_data = await spider.collect(
                keyword=keyword,
                user_id=user_id,
                url=url,
                max_count=max_count,
                filters=filters,
                **kwargs
            )

            # Match and deduplicate
            matched_data = await self.matcher_manager.match(
                platform=platform,
                data=raw_data
            )

            # Process interactions
            processed_data = await self.interaction_manager.process(
                platform=platform,
                data=matched_data
            )

            # Save to database
            await self.db.save_collection(
                platform=platform,
                data=processed_data
            )

            logger.info(f"Data collection completed: {len(processed_data)} items")

            return {
                "platform": platform,
                "count": len(processed_data),
                "data": processed_data,
                "meta": {
                    "keyword": keyword,
                    "user_id": user_id,
                    "url": url,
                    "filters": filters
                }
            }

        except Exception as e:
            logger.error(f"Error collecting data from {platform}: {e}")
            raise

    def collect(
        self,
        platform: str,
        keyword: Optional[str] = None,
        user_id: Optional[str] = None,
        url: Optional[str] = None,
        max_count: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步采集平台数据（异步方法的同步包装）

        Args:
            platform: 平台名称
            keyword: 搜索关键词
            user_id: 用户ID
            url: 直接URL
            max_count: 最大采集数量
            filters: 过滤条件
            **kwargs: 平台特定参数

        Returns:
            采集结果字典
        """
        return asyncio.run(self.collect_async(
            platform=platform,
            keyword=keyword,
            user_id=user_id,
            url=url,
            max_count=max_count,
            filters=filters,
            **kwargs
        ))

    async def analyze_async(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        agents: Optional[List[str]] = None,
        analysis_types: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步分析数据

        Args:
            data: 采集的数据
            agents: 使用的Agent列表 (scout, analyst, ecommerce, academic, creator, report)
            analysis_types: 分析类型 (sentiment, clustering, prediction, comparison)
            **kwargs: 其他参数

        Returns:
            分析结果字典
        """
        logger.info("Starting data analysis...")

        try:
            results = {}

            # Run agents if specified
            if agents:
                agent_results = await self.agent_manager.run_agents(
                    agents=agents,
                    data=data,
                    **kwargs
                )
                results["agents"] = agent_results

            # Run analysis engine
            if analysis_types:
                analysis_results = await self.analysis_engine.analyze(
                    data=data,
                    analysis_types=analysis_types,
                    **kwargs
                )
                results["analysis"] = analysis_results

            # If no specific analysis requested, run default analysis
            if not agents and not analysis_types:
                results["analysis"] = await self.analysis_engine.analyze(
                    data=data,
                    analysis_types=["sentiment", "clustering"],
                    **kwargs
                )

            logger.info("Data analysis completed")
            return results

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            raise

    def analyze(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        agents: Optional[List[str]] = None,
        analysis_types: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步分析数据（异步方法的同步包装）

        Args:
            data: 采集的数据
            agents: 使用的Agent列表
            analysis_types: 分析类型
            **kwargs: 其他参数

        Returns:
            分析结果字典
        """
        return asyncio.run(self.analyze_async(
            data=data,
            agents=agents,
            analysis_types=analysis_types,
            **kwargs
        ))

    def visualize(
        self,
        data: Dict[str, Any],
        chart_types: Optional[List[str]] = None,
        output: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        可视化数据

        Args:
            data: 分析数据
            chart_types: 图表类型 (line, bar, pie, wordcloud, network)
            output: 输出文件路径
            **kwargs: 其他参数

        Returns:
            可视化结果（图表对象或文件路径）
        """
        logger.info("Generating visualizations...")

        try:
            charts = self.viz_renderer.render(
                data=data,
                chart_types=chart_types or ["bar", "wordcloud"],
                output=output,
                **kwargs
            )

            logger.info("Visualizations generated successfully")
            return charts

        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
            raise

    def generate_report(
        self,
        analysis: Dict[str, Any],
        format: str = "pdf",
        output: str = "report.pdf",
        template: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        生成报告

        Args:
            analysis: 分析结果
            format: 报告格式 (pdf, docx, html, md)
            output: 输出文件路径
            template: 报告模板
            **kwargs: 其他参数

        Returns:
            报告文件路径
        """
        logger.info(f"Generating {format.upper()} report...")

        try:
            report_path = self.agent_manager.generate_report(
                analysis=analysis,
                format=format,
                output=output,
                template=template,
                **kwargs
            )

            logger.info(f"Report generated: {report_path}")
            return report_path

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise

    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return self.spider_manager.get_supported_platforms()

    def get_platform_info(self, platform: str) -> Dict[str, Any]:
        """获取平台详细信息"""
        return self.spider_manager.get_platform_info(platform)

    async def close(self):
        """关闭所有连接"""
        logger.info("Closing OmniSense system...")
        await self.db.close()
        await self.spider_manager.close()
        logger.info("OmniSense system closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        asyncio.run(self.close())

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def generate_advanced_report(
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
        生成高级报告（使用ReportEngine）

        Args:
            query: 报告查询/主题
            data_summary: 数据摘要
            analysis_results: 分析结果
            template_name: 模板名称
            target_words: 目标字数
            output_format: 输出格式 (html/pdf/markdown)
            output_path: 输出路径
            **kwargs: 额外参数

        Returns:
            报告生成结果
        """
        try:
            from omnisense.report.engine import ReportEngine

            logger.info(f"Generating advanced report: {query}")

            # Initialize report engine
            report_engine = ReportEngine(
                llm=self.agent_manager.agents.get('analyst').llm if self.agent_manager.agents else None,
                config=kwargs.get('report_config', {})
            )

            # Generate report
            result = await report_engine.generate_report(
                query=query,
                data_summary=data_summary,
                analysis_results=analysis_results,
                template_name=template_name,
                target_words=target_words,
                output_format=output_format,
                output_path=output_path,
                **kwargs
            )

            logger.info(f"Advanced report generated: {result.get('output_path', 'N/A')}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate advanced report: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def start_agent_forum(
        self,
        topic: str,
        agent_ids: Optional[List[str]] = None,
        max_rounds: int = 10,
        timeout_seconds: int = 300,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        启动Agent论坛讨论会话（使用ForumEngine）

        Args:
            topic: 讨论主题
            agent_ids: 参与Agent ID列表（None表示所有Agent）
            max_rounds: 最大讨论轮次
            timeout_seconds: 超时时间
            initial_context: 初始上下文

        Returns:
            论坛会话信息
        """
        try:
            logger.info(f"Starting agent forum on topic: {topic}")

            # Initialize forum if not already initialized
            if not hasattr(self.agent_manager, 'forum_engine') or not self.agent_manager.forum_engine:
                # Get LLM from first available agent
                llm = None
                for agent in self.agent_manager.agents.values():
                    if hasattr(agent, 'llm'):
                        llm = agent.llm
                        break

                if not llm:
                    return {
                        "success": False,
                        "error": "No LLM available for forum initialization"
                    }

                self.agent_manager.initialize_forum(llm=llm)

            # Start forum session
            session_id = await self.agent_manager.start_forum_session(
                topic=topic,
                agent_ids=agent_ids,
                max_rounds=max_rounds,
                timeout_seconds=timeout_seconds,
                initial_context=initial_context
            )

            result = {
                "success": True,
                "session_id": session_id,
                "topic": topic,
                "agents": agent_ids or list(self.agent_manager.agents.keys()),
                "max_rounds": max_rounds
            }

            logger.info(f"Agent forum started: {session_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to start agent forum: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def build_knowledge_graph(
        self,
        documents: List[Dict[str, Any]],
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        batch_size: int = 10,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        构建知识图谱（使用GraphRAG）

        Args:
            documents: 文档列表，每个文档包含 {'text', 'id', 'metadata'}
            neo4j_uri: Neo4j URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            batch_size: 批处理大小
            use_llm: 是否使用LLM进行关系抽取

        Returns:
            知识图谱构建结果
        """
        try:
            from omnisense.graphrag import (
                Neo4jStorage,
                EntityExtractor,
                RelationExtractor,
                KnowledgeGraphBuilder
            )

            logger.info(f"Building knowledge graph from {len(documents)} documents")

            # Initialize components
            storage = Neo4jStorage(
                uri=neo4j_uri,
                username=neo4j_user,
                password=neo4j_password
            )

            entity_extractor = EntityExtractor()

            # Get LLM if requested
            llm = None
            if use_llm:
                for agent in self.agent_manager.agents.values():
                    if hasattr(agent, 'llm'):
                        llm = agent.llm
                        break

            relation_extractor = RelationExtractor(llm=llm, use_patterns=True)

            builder = KnowledgeGraphBuilder(
                storage=storage,
                entity_extractor=entity_extractor,
                relation_extractor=relation_extractor
            )

            # Build graph
            result = await builder.build_from_documents_async(
                documents=documents,
                max_concurrent=batch_size
            )

            # Create indexes
            builder.create_indexes()

            # Get statistics
            stats = builder.get_statistics()

            # Close storage
            storage.close()

            final_result = {
                "success": True,
                "build_result": result,
                "statistics": stats
            }

            logger.info(f"Knowledge graph built: {result.get('total_entities', 0)} entities, {result.get('total_relations', 0)} relations")
            return final_result

        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            return {
                "success": False,
                "error": str(e)
            }
