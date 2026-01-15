"""
Scout Agent - Data Exploration and Discovery
负责数据探索、初步分析和信息发现
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole, AgentResponse, AgentState


class ScoutAgent(BaseAgent):
    """
    Scout agent for data exploration and discovery

    Capabilities:
    - Platform content discovery
    - Trend identification
    - Keyword extraction
    - Data quality assessment
    - Quick insights generation
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Scout",
                role=AgentRole.SCOUT,
                system_prompt=self._get_system_prompt()
            )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a Scout Agent specialized in data exploration and discovery.

Your role:
1. Explore and discover content across platforms
2. Identify trending topics and patterns
3. Extract key information and keywords
4. Assess data quality and relevance
5. Provide quick insights for further analysis

Approach:
- Be thorough but efficient
- Focus on high-value signals
- Identify patterns and anomalies
- Prioritize actionable insights
- Use structured output formats

Output format:
Always provide responses in this structure:
{
  "discoveries": [...],
  "trends": [...],
  "keywords": [...],
  "quality_score": 0-100,
  "recommendations": [...]
}
"""

    def _setup_chains(self):
        """Setup LangChain chains for scout operations"""
        # Discovery chain
        self._create_chain(
            name="discovery",
            template="""
Analyze the following data and identify key discoveries:

Data: {data}
Platform: {platform}
Context: {context}

Provide:
1. Main content themes
2. Notable patterns
3. Key entities (users, products, topics)
4. Engagement indicators
5. Data quality assessment

Response:
""",
            input_variables=["data", "platform", "context"]
        )

        # Trend analysis chain
        self._create_chain(
            name="trend_analysis",
            template="""
Analyze trends in the following data:

Data: {data}
Timeframe: {timeframe}

Identify:
1. Emerging trends
2. Declining topics
3. Seasonal patterns
4. Viral content
5. Anomalies

Trends:
""",
            input_variables=["data", "timeframe"]
        )

        # Keyword extraction chain
        self._create_chain(
            name="keyword_extraction",
            template="""
Extract and rank keywords from the following content:

Content: {content}
Language: {language}

Extract:
1. Primary keywords (most important)
2. Secondary keywords (supporting)
3. Long-tail phrases
4. Named entities
5. Hashtags/tags

Keywords:
""",
            input_variables=["content", "language"]
        )

    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process scout task

        Task types:
        - discover: Explore and discover content
        - analyze_trends: Identify trends
        - extract_keywords: Extract keywords
        - assess_quality: Assess data quality
        """
        self.state = AgentState.WORKING
        context = context or {}

        try:
            task_type = task.get("type", "discover")

            if task_type == "discover":
                result = await self._discover(task, context)
            elif task_type == "analyze_trends":
                result = await self._analyze_trends(task, context)
            elif task_type == "extract_keywords":
                result = await self._extract_keywords(task, context)
            elif task_type == "assess_quality":
                result = await self._assess_quality(task, context)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            logger.error(f"Scout processing failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def _discover(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Discover and explore content"""
        data = task.get("data", [])
        platform = task.get("platform", "unknown")

        # Generate reasoning steps
        reasoning = await self.think(
            f"Explore content from {platform}",
            {"data_size": len(data), "platform": platform}
        )

        # Run discovery chain
        chain_result = await self._execute_with_retry(
            self.chains["discovery"].ainvoke,
            {
                "data": str(data)[:5000],  # Limit data size
                "platform": platform,
                "context": str(context)
            }
        )

        # Parse discoveries
        discoveries = self._parse_discoveries(chain_result["text"])

        # Calculate confidence
        confidence = min(0.9, len(discoveries) / 10.0)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "discoveries": discoveries,
                "platform": platform,
                "data_size": len(data)
            },
            message=f"Discovered {len(discoveries)} key insights from {platform}",
            reasoning=reasoning,
            confidence=confidence,
            metadata={
                "task_type": "discover",
                "platform": platform
            }
        )

    async def _analyze_trends(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze trends in data"""
        data = task.get("data", [])
        timeframe = task.get("timeframe", "recent")

        reasoning = await self.think(
            f"Analyze trends in {timeframe} data",
            {"data_size": len(data)}
        )

        # Run trend analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["trend_analysis"].ainvoke,
            {
                "data": str(data)[:5000],
                "timeframe": timeframe
            }
        )

        trends = self._parse_trends(chain_result["text"])

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "trends": trends,
                "timeframe": timeframe,
                "trend_count": len(trends)
            },
            message=f"Identified {len(trends)} trends in {timeframe} data",
            reasoning=reasoning,
            confidence=0.8,
            metadata={
                "task_type": "analyze_trends",
                "timeframe": timeframe
            }
        )

    async def _extract_keywords(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Extract keywords from content"""
        content = task.get("content", "")
        language = task.get("language", "auto")

        reasoning = await self.think(
            "Extract keywords from content",
            {"content_length": len(content)}
        )

        # Run keyword extraction chain
        chain_result = await self._execute_with_retry(
            self.chains["keyword_extraction"].ainvoke,
            {
                "content": content[:3000],
                "language": language
            }
        )

        keywords = self._parse_keywords(chain_result["text"])

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "keywords": keywords,
                "language": language,
                "keyword_count": len(keywords)
            },
            message=f"Extracted {len(keywords)} keywords",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "extract_keywords",
                "language": language
            }
        )

    async def _assess_quality(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Assess data quality"""
        data = task.get("data", [])

        # Quality metrics
        metrics = {
            "completeness": self._check_completeness(data),
            "consistency": self._check_consistency(data),
            "accuracy": self._check_accuracy(data),
            "relevance": self._check_relevance(data, context)
        }

        overall_score = sum(metrics.values()) / len(metrics)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "quality_metrics": metrics,
                "overall_score": overall_score,
                "passed": overall_score >= 0.7
            },
            message=f"Quality score: {overall_score:.2f}",
            reasoning=[
                f"Completeness: {metrics['completeness']:.2f}",
                f"Consistency: {metrics['consistency']:.2f}",
                f"Accuracy: {metrics['accuracy']:.2f}",
                f"Relevance: {metrics['relevance']:.2f}"
            ],
            confidence=0.9,
            metadata={
                "task_type": "assess_quality"
            }
        )

    def _parse_discoveries(self, text: str) -> List[Dict[str, Any]]:
        """Parse discoveries from LLM output"""
        discoveries = []
        lines = text.split('\n')

        current_discovery = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_discovery:
                    discoveries.append(current_discovery)
                    current_discovery = {}
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                current_discovery[key.strip().lower()] = value.strip()

        if current_discovery:
            discoveries.append(current_discovery)

        return discoveries

    def _parse_trends(self, text: str) -> List[Dict[str, Any]]:
        """Parse trends from LLM output"""
        trends = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Remove numbering/bullets
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    trends.append({
                        "trend": content,
                        "type": "emerging" if "emerging" in content.lower() else "general"
                    })

        return trends

    def _parse_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Parse keywords from LLM output"""
        keywords = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    keywords.append({
                        "keyword": content,
                        "category": "primary"  # Could be enhanced with classification
                    })

        return keywords[:20]  # Top 20 keywords

    def _check_completeness(self, data: List[Any]) -> float:
        """Check data completeness"""
        if not data:
            return 0.0

        # Check for missing values
        total_fields = 0
        missing_fields = 0

        for item in data[:100]:  # Sample first 100
            if isinstance(item, dict):
                for value in item.values():
                    total_fields += 1
                    if value is None or value == "":
                        missing_fields += 1

        if total_fields == 0:
            return 0.0

        return 1.0 - (missing_fields / total_fields)

    def _check_consistency(self, data: List[Any]) -> float:
        """Check data consistency"""
        if not data:
            return 0.0

        # Check schema consistency
        if not all(isinstance(item, type(data[0])) for item in data):
            return 0.5

        if isinstance(data[0], dict):
            first_keys = set(data[0].keys())
            consistency_scores = [
                len(first_keys.intersection(item.keys())) / len(first_keys)
                for item in data
                if isinstance(item, dict)
            ]
            return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0

        return 1.0

    def _check_accuracy(self, data: List[Any]) -> float:
        """Check data accuracy (basic heuristics)"""
        if not data:
            return 0.0

        # Basic accuracy checks
        accuracy_score = 1.0

        for item in data[:50]:
            if isinstance(item, dict):
                # Check for reasonable values
                for key, value in item.items():
                    if isinstance(value, (int, float)):
                        if value < 0 and key not in ["temperature", "balance", "change"]:
                            accuracy_score *= 0.95

        return accuracy_score

    def _check_relevance(self, data: List[Any], context: Dict[str, Any]) -> float:
        """Check data relevance to context"""
        if not data or not context:
            return 0.5

        # Basic relevance scoring
        relevance_score = 0.7  # Default baseline

        # Check if context keywords appear in data
        context_keywords = context.get("keywords", [])
        if context_keywords:
            matches = 0
            for item in data[:50]:
                item_str = str(item).lower()
                for keyword in context_keywords:
                    if keyword.lower() in item_str:
                        matches += 1

            relevance_score = min(1.0, 0.5 + (matches / (len(data[:50]) * len(context_keywords))))

        return relevance_score
