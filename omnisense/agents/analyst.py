"""
Analyst Agent - Deep Data Analysis
负责深度数据分析、统计分析和洞察生成
"""

from typing import Any, Dict, List, Optional
import json
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole, AgentResponse, AgentState


class AnalystAgent(BaseAgent):
    """
    Analyst agent for deep data analysis

    Capabilities:
    - Statistical analysis
    - Sentiment analysis
    - Pattern recognition
    - Correlation analysis
    - Predictive insights
    - Comparative analysis
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Analyst",
                role=AgentRole.ANALYST,
                system_prompt=self._get_system_prompt()
            )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are an Analyst Agent specialized in deep data analysis and insights generation.

Your role:
1. Perform statistical and quantitative analysis
2. Identify patterns, correlations, and causations
3. Conduct sentiment and opinion analysis
4. Generate predictive insights
5. Provide comparative analysis across datasets
6. Deliver actionable recommendations

Approach:
- Use rigorous analytical methods
- Support conclusions with data evidence
- Identify statistical significance
- Consider multiple perspectives
- Highlight limitations and assumptions
- Focus on actionable insights

Output format:
Always provide structured analysis with:
{
  "summary": "...",
  "key_findings": [...],
  "statistics": {...},
  "insights": [...],
  "recommendations": [...],
  "confidence_level": "high|medium|low"
}
"""

    def _setup_chains(self):
        """Setup LangChain chains for analyst operations"""
        # Deep analysis chain
        self._create_chain(
            name="deep_analysis",
            template="""
Perform deep analysis on the following data:

Data: {data}
Analysis Type: {analysis_type}
Context: {context}

Provide comprehensive analysis including:
1. Data summary and overview
2. Key statistical findings
3. Patterns and trends
4. Anomalies and outliers
5. Correlations and relationships
6. Actionable insights
7. Recommendations

Analysis:
""",
            input_variables=["data", "analysis_type", "context"]
        )

        # Sentiment analysis chain
        self._create_chain(
            name="sentiment_analysis",
            template="""
Analyze sentiment in the following content:

Content: {content}
Platform: {platform}

Provide:
1. Overall sentiment (positive/negative/neutral)
2. Sentiment distribution
3. Key emotional indicators
4. Sentiment drivers (what causes the sentiment)
5. Notable quotes or examples
6. Sentiment trends over time (if applicable)

Sentiment Analysis:
""",
            input_variables=["content", "platform"]
        )

        # Pattern recognition chain
        self._create_chain(
            name="pattern_recognition",
            template="""
Identify patterns in the following data:

Data: {data}
Timeframe: {timeframe}
Dimensions: {dimensions}

Identify:
1. Recurring patterns
2. Cyclical behaviors
3. Sequential patterns
4. Clustering patterns
5. Anomalous patterns
6. Predictive patterns

Patterns:
""",
            input_variables=["data", "timeframe", "dimensions"]
        )

        # Comparative analysis chain
        self._create_chain(
            name="comparative_analysis",
            template="""
Compare the following datasets:

Dataset A: {dataset_a}
Dataset B: {dataset_b}
Comparison Criteria: {criteria}

Provide:
1. Similarities
2. Differences
3. Relative performance
4. Competitive advantages/disadvantages
5. Statistical comparison
6. Insights and implications

Comparison:
""",
            input_variables=["dataset_a", "dataset_b", "criteria"]
        )

    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process analyst task

        Task types:
        - deep_analysis: Comprehensive analysis
        - sentiment_analysis: Sentiment analysis
        - pattern_recognition: Pattern identification
        - comparative_analysis: Compare datasets
        - statistical_analysis: Statistical analysis
        """
        self.state = AgentState.WORKING
        context = context or {}

        try:
            task_type = task.get("type", "deep_analysis")

            if task_type == "deep_analysis":
                result = await self._deep_analysis(task, context)
            elif task_type == "sentiment_analysis":
                result = await self._sentiment_analysis(task, context)
            elif task_type == "pattern_recognition":
                result = await self._pattern_recognition(task, context)
            elif task_type == "comparative_analysis":
                result = await self._comparative_analysis(task, context)
            elif task_type == "statistical_analysis":
                result = await self._statistical_analysis(task, context)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            logger.error(f"Analyst processing failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def _deep_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Perform deep data analysis"""
        data = task.get("data", [])
        analysis_type = task.get("analysis_type", "general")

        reasoning = await self.think(
            f"Perform {analysis_type} analysis on data",
            {"data_size": len(data), "type": analysis_type}
        )

        # Run deep analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["deep_analysis"].ainvoke,
            {
                "data": str(data)[:5000],
                "analysis_type": analysis_type,
                "context": str(context)
            }
        )

        # Parse analysis results
        analysis = self._parse_analysis(chain_result["text"])

        # Compute statistics
        statistics = self._compute_statistics(data)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "analysis": analysis,
                "statistics": statistics,
                "analysis_type": analysis_type,
                "data_size": len(data)
            },
            message=f"Completed {analysis_type} analysis with {len(analysis.get('insights', []))} key insights",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "deep_analysis",
                "analysis_type": analysis_type
            }
        )

    async def _sentiment_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze sentiment in content"""
        content = task.get("content", "")
        platform = task.get("platform", "unknown")

        reasoning = await self.think(
            f"Analyze sentiment from {platform}",
            {"content_length": len(content)}
        )

        # Run sentiment analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["sentiment_analysis"].ainvoke,
            {
                "content": content[:4000],
                "platform": platform
            }
        )

        # Parse sentiment
        sentiment_data = self._parse_sentiment(chain_result["text"])

        # Basic sentiment scoring
        sentiment_scores = self._compute_sentiment_scores(content)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "sentiment": sentiment_data,
                "scores": sentiment_scores,
                "platform": platform
            },
            message=f"Sentiment: {sentiment_data.get('overall', 'neutral')} "
                    f"(score: {sentiment_scores.get('compound', 0):.2f})",
            reasoning=reasoning,
            confidence=0.8,
            metadata={
                "task_type": "sentiment_analysis",
                "platform": platform
            }
        )

    async def _pattern_recognition(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Identify patterns in data"""
        data = task.get("data", [])
        timeframe = task.get("timeframe", "all")
        dimensions = task.get("dimensions", ["time", "value"])

        reasoning = await self.think(
            f"Identify patterns in {timeframe} data",
            {"data_size": len(data), "dimensions": dimensions}
        )

        # Run pattern recognition chain
        chain_result = await self._execute_with_retry(
            self.chains["pattern_recognition"].ainvoke,
            {
                "data": str(data)[:5000],
                "timeframe": timeframe,
                "dimensions": str(dimensions)
            }
        )

        patterns = self._parse_patterns(chain_result["text"])

        # Statistical pattern detection
        statistical_patterns = self._detect_statistical_patterns(data)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "patterns": patterns,
                "statistical_patterns": statistical_patterns,
                "pattern_count": len(patterns),
                "timeframe": timeframe
            },
            message=f"Identified {len(patterns)} patterns in {timeframe} data",
            reasoning=reasoning,
            confidence=0.75,
            metadata={
                "task_type": "pattern_recognition",
                "timeframe": timeframe
            }
        )

    async def _comparative_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Compare multiple datasets"""
        dataset_a = task.get("dataset_a", [])
        dataset_b = task.get("dataset_b", [])
        criteria = task.get("criteria", "general")

        reasoning = await self.think(
            f"Compare datasets by {criteria}",
            {"size_a": len(dataset_a), "size_b": len(dataset_b)}
        )

        # Run comparative analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["comparative_analysis"].ainvoke,
            {
                "dataset_a": str(dataset_a)[:2500],
                "dataset_b": str(dataset_b)[:2500],
                "criteria": criteria
            }
        )

        comparison = self._parse_comparison(chain_result["text"])

        # Statistical comparison
        stats_comparison = self._compare_statistics(dataset_a, dataset_b)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "comparison": comparison,
                "statistics": stats_comparison,
                "criteria": criteria
            },
            message=f"Completed comparative analysis by {criteria}",
            reasoning=reasoning,
            confidence=0.82,
            metadata={
                "task_type": "comparative_analysis",
                "criteria": criteria
            }
        )

    async def _statistical_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Perform statistical analysis"""
        data = task.get("data", [])

        reasoning = await self.think(
            "Perform statistical analysis",
            {"data_size": len(data)}
        )

        # Compute comprehensive statistics
        statistics = self._compute_comprehensive_statistics(data)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "statistics": statistics,
                "data_size": len(data)
            },
            message=f"Statistical analysis completed on {len(data)} data points",
            reasoning=reasoning,
            confidence=0.9,
            metadata={
                "task_type": "statistical_analysis"
            }
        )

    def _parse_analysis(self, text: str) -> Dict[str, Any]:
        """Parse analysis results"""
        analysis = {
            "summary": "",
            "insights": [],
            "recommendations": []
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if "summary" in line.lower():
                current_section = "summary"
            elif "insight" in line.lower() or "finding" in line.lower():
                current_section = "insights"
            elif "recommend" in line.lower():
                current_section = "recommendations"
            elif current_section:
                if current_section == "summary":
                    analysis["summary"] += line + " "
                elif line[0].isdigit() or line.startswith(('-', '•')):
                    content = line.lstrip('0123456789.-• ').strip()
                    if content:
                        analysis[current_section].append(content)

        return analysis

    def _parse_sentiment(self, text: str) -> Dict[str, Any]:
        """Parse sentiment analysis results"""
        sentiment = {
            "overall": "neutral",
            "distribution": {},
            "drivers": []
        }

        for line in text.split('\n'):
            line_lower = line.lower()
            if "overall" in line_lower:
                if "positive" in line_lower:
                    sentiment["overall"] = "positive"
                elif "negative" in line_lower:
                    sentiment["overall"] = "negative"

        return sentiment

    def _parse_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Parse pattern recognition results"""
        patterns = []
        for line in text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    patterns.append({
                        "pattern": content,
                        "type": "identified"
                    })
        return patterns

    def _parse_comparison(self, text: str) -> Dict[str, Any]:
        """Parse comparison results"""
        comparison = {
            "similarities": [],
            "differences": [],
            "winner": "tie"
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if "similar" in line.lower():
                current_section = "similarities"
            elif "differ" in line.lower():
                current_section = "differences"
            elif current_section and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    comparison[current_section].append(content)

        return comparison

    def _compute_statistics(self, data: List[Any]) -> Dict[str, Any]:
        """Compute basic statistics"""
        if not data:
            return {}

        stats = {
            "count": len(data),
            "type": str(type(data[0]).__name__) if data else "unknown"
        }

        # Extract numeric values if possible
        numeric_values = []
        for item in data:
            if isinstance(item, (int, float)):
                numeric_values.append(item)
            elif isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, (int, float)):
                        numeric_values.append(v)

        if numeric_values:
            stats.update({
                "mean": sum(numeric_values) / len(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values),
                "range": max(numeric_values) - min(numeric_values)
            })

        return stats

    def _compute_comprehensive_statistics(self, data: List[Any]) -> Dict[str, Any]:
        """Compute comprehensive statistics"""
        stats = self._compute_statistics(data)

        # Add more detailed statistics
        numeric_values = []
        for item in data:
            if isinstance(item, (int, float)):
                numeric_values.append(item)

        if numeric_values and len(numeric_values) > 1:
            # Variance and std dev
            mean = sum(numeric_values) / len(numeric_values)
            variance = sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)
            stats["variance"] = variance
            stats["std_dev"] = variance ** 0.5

            # Median
            sorted_values = sorted(numeric_values)
            mid = len(sorted_values) // 2
            if len(sorted_values) % 2 == 0:
                stats["median"] = (sorted_values[mid - 1] + sorted_values[mid]) / 2
            else:
                stats["median"] = sorted_values[mid]

        return stats

    def _compute_sentiment_scores(self, content: str) -> Dict[str, float]:
        """Compute basic sentiment scores"""
        # Simple keyword-based sentiment
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "love", "best"]
        negative_words = ["bad", "poor", "terrible", "awful", "hate", "worst", "disappointing"]

        content_lower = content.lower()
        pos_count = sum(1 for word in positive_words if word in content_lower)
        neg_count = sum(1 for word in negative_words if word in content_lower)

        total = pos_count + neg_count
        if total == 0:
            compound = 0.0
        else:
            compound = (pos_count - neg_count) / total

        return {
            "positive": pos_count / max(total, 1),
            "negative": neg_count / max(total, 1),
            "neutral": 1.0 - (pos_count + neg_count) / max(total, 1),
            "compound": compound
        }

    def _detect_statistical_patterns(self, data: List[Any]) -> List[Dict[str, Any]]:
        """Detect statistical patterns"""
        patterns = []

        if len(data) < 3:
            return patterns

        # Trend detection
        numeric_values = []
        for item in data:
            if isinstance(item, (int, float)):
                numeric_values.append(item)

        if len(numeric_values) >= 3:
            # Simple trend detection
            diffs = [numeric_values[i+1] - numeric_values[i] for i in range(len(numeric_values)-1)]
            if all(d > 0 for d in diffs):
                patterns.append({"type": "increasing_trend", "confidence": 0.9})
            elif all(d < 0 for d in diffs):
                patterns.append({"type": "decreasing_trend", "confidence": 0.9})

        return patterns

    def _compare_statistics(self, dataset_a: List[Any], dataset_b: List[Any]) -> Dict[str, Any]:
        """Compare statistics between datasets"""
        stats_a = self._compute_statistics(dataset_a)
        stats_b = self._compute_statistics(dataset_b)

        comparison = {
            "dataset_a": stats_a,
            "dataset_b": stats_b,
            "differences": {}
        }

        # Compare common metrics
        for key in ["count", "mean", "min", "max"]:
            if key in stats_a and key in stats_b:
                comparison["differences"][key] = stats_a[key] - stats_b[key]

        return comparison
