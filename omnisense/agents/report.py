"""
Report Agent - Document Generation and Reporting
负责报告生成、数据可视化和文档输出
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole, AgentResponse, AgentState


class ReportAgent(BaseAgent):
    """
    Report agent for document generation and reporting

    Capabilities:
    - Comprehensive report generation
    - Executive summary creation
    - Data visualization recommendations
    - Multi-format export (PDF, HTML, Markdown)
    - Template-based reporting
    - Automated insight summarization
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Report",
                role=AgentRole.REPORT,
                system_prompt=self._get_system_prompt()
            )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a Report Agent specialized in document generation and reporting.

Your role:
1. Generate comprehensive, well-structured reports
2. Create executive summaries for decision-makers
3. Synthesize complex data into clear insights
4. Recommend appropriate visualizations
5. Format reports for different audiences
6. Ensure clarity, accuracy, and professionalism

Approach:
- Structure information logically
- Use clear, concise language
- Highlight key insights and recommendations
- Support claims with data evidence
- Adapt tone and detail to audience
- Include actionable next steps

Output format:
Always provide structured reports with:
{
  "title": "...",
  "executive_summary": "...",
  "sections": [...],
  "key_insights": [...],
  "recommendations": [...],
  "visualizations": [...],
  "metadata": {...}
}
"""

    def _setup_chains(self):
        """Setup LangChain chains for report operations"""
        # Executive summary chain
        self._create_chain(
            name="executive_summary",
            template="""
Create an executive summary for the following data:

Data Analysis: {analysis}
Key Findings: {findings}
Context: {context}

Provide a concise executive summary (200-300 words) that:
1. Highlights the most important findings
2. Explains business implications
3. Provides clear recommendations
4. Uses language accessible to executives

Executive Summary:
""",
            input_variables=["analysis", "findings", "context"]
        )

        # Report generation chain
        self._create_chain(
            name="report_generation",
            template="""
Generate a comprehensive report on:

Topic: {topic}
Data: {data}
Analysis Results: {analysis}
Audience: {audience}

Create a detailed report with:
1. Introduction and background
2. Methodology (if applicable)
3. Detailed findings with evidence
4. Analysis and interpretation
5. Insights and implications
6. Recommendations and next steps
7. Conclusion

Report:
""",
            input_variables=["topic", "data", "analysis", "audience"]
        )

        # Insight synthesis chain
        self._create_chain(
            name="insight_synthesis",
            template="""
Synthesize insights from multiple sources:

Source 1: {source_1}
Source 2: {source_2}
Source 3: {source_3}
Context: {context}

Provide synthesized insights that:
1. Identify common themes
2. Highlight contradictions or tensions
3. Draw cross-cutting conclusions
4. Provide holistic perspective
5. Generate actionable recommendations

Synthesized Insights:
""",
            input_variables=["source_1", "source_2", "source_3", "context"]
        )

        # Visualization recommendation chain
        self._create_chain(
            name="visualization_recommendation",
            template="""
Recommend visualizations for:

Data Type: {data_type}
Data Size: {data_size}
Story to Tell: {story}
Audience: {audience}

Recommend:
1. Most effective chart/graph types
2. Key metrics to visualize
3. Layout and composition suggestions
4. Color and styling recommendations
5. Interactive elements (if applicable)

Visualization Recommendations:
""",
            input_variables=["data_type", "data_size", "story", "audience"]
        )

    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process report task

        Task types:
        - generate_report: Generate comprehensive report
        - executive_summary: Create executive summary
        - synthesize_insights: Synthesize insights
        - recommend_visualizations: Recommend charts/graphs
        - format_report: Format report for specific output
        """
        self.state = AgentState.WORKING
        context = context or {}

        try:
            task_type = task.get("type", "generate_report")

            if task_type == "generate_report":
                result = await self._generate_report(task, context)
            elif task_type == "executive_summary":
                result = await self._executive_summary(task, context)
            elif task_type == "synthesize_insights":
                result = await self._synthesize_insights(task, context)
            elif task_type == "recommend_visualizations":
                result = await self._recommend_visualizations(task, context)
            elif task_type == "format_report":
                result = await self._format_report(task, context)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            logger.error(f"Report processing failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def _generate_report(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Generate comprehensive report"""
        topic = task.get("topic", "")
        data = task.get("data", {})
        analysis = task.get("analysis", {})
        audience = task.get("audience", "general")
        template = task.get("template", "standard")

        reasoning = await self.think(
            f"Generate {template} report on {topic}",
            {"audience": audience}
        )

        # Run report generation chain
        chain_result = await self._execute_with_retry(
            self.chains["report_generation"].ainvoke,
            {
                "topic": topic,
                "data": str(data)[:3000],
                "analysis": str(analysis)[:3000],
                "audience": audience
            }
        )

        # Parse report sections
        sections = self._parse_report_sections(chain_result["text"])

        # Generate metadata
        metadata = self._generate_report_metadata(topic, audience, template)

        # Build complete report
        report = self._build_report_structure(
            topic=topic,
            sections=sections,
            metadata=metadata,
            template=template
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "report": report,
                "topic": topic,
                "section_count": len(sections),
                "template": template
            },
            message=f"Generated {template} report on {topic} "
                    f"({len(sections)} sections)",
            reasoning=reasoning,
            confidence=0.88,
            metadata={
                "task_type": "generate_report",
                "template": template,
                "audience": audience
            }
        )

    async def _executive_summary(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Create executive summary"""
        analysis = task.get("analysis", {})
        findings = task.get("findings", [])

        reasoning = await self.think(
            "Create executive summary",
            {"finding_count": len(findings)}
        )

        # Run executive summary chain
        chain_result = await self._execute_with_retry(
            self.chains["executive_summary"].ainvoke,
            {
                "analysis": str(analysis)[:2000],
                "findings": str(findings)[:2000],
                "context": str(context)[:1000]
            }
        )

        summary = chain_result["text"].strip()

        # Extract key points
        key_points = self._extract_key_points(summary)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "summary": summary,
                "key_points": key_points,
                "word_count": len(summary.split())
            },
            message=f"Executive summary created ({len(summary.split())} words)",
            reasoning=reasoning,
            confidence=0.9,
            metadata={
                "task_type": "executive_summary"
            }
        )

    async def _synthesize_insights(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Synthesize insights from multiple sources"""
        sources = task.get("sources", [])

        if len(sources) < 2:
            raise ValueError("At least 2 sources required for synthesis")

        reasoning = await self.think(
            f"Synthesize insights from {len(sources)} sources",
            {}
        )

        # Prepare sources for synthesis
        source_1 = str(sources[0])[:2000] if len(sources) > 0 else ""
        source_2 = str(sources[1])[:2000] if len(sources) > 1 else ""
        source_3 = str(sources[2])[:2000] if len(sources) > 2 else ""

        # Run insight synthesis chain
        chain_result = await self._execute_with_retry(
            self.chains["insight_synthesis"].ainvoke,
            {
                "source_1": source_1,
                "source_2": source_2,
                "source_3": source_3,
                "context": str(context)[:1000]
            }
        )

        # Parse synthesized insights
        insights = self._parse_synthesized_insights(chain_result["text"])

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "synthesized_insights": insights,
                "source_count": len(sources),
                "insight_count": len(insights)
            },
            message=f"Synthesized {len(insights)} insights from {len(sources)} sources",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "synthesize_insights",
                "source_count": len(sources)
            }
        )

    async def _recommend_visualizations(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Recommend visualizations"""
        data_type = task.get("data_type", "mixed")
        data_size = task.get("data_size", "medium")
        story = task.get("story", "")
        audience = task.get("audience", "general")

        reasoning = await self.think(
            f"Recommend visualizations for {data_type} data",
            {"story": story, "audience": audience}
        )

        # Run visualization recommendation chain
        chain_result = await self._execute_with_retry(
            self.chains["visualization_recommendation"].ainvoke,
            {
                "data_type": data_type,
                "data_size": data_size,
                "story": story,
                "audience": audience
            }
        )

        # Parse recommendations
        viz_recommendations = self._parse_visualization_recommendations(
            chain_result["text"]
        )

        # Add specific chart suggestions
        chart_suggestions = self._generate_chart_suggestions(
            data_type,
            data_size,
            story
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "recommendations": viz_recommendations,
                "chart_suggestions": chart_suggestions,
                "data_type": data_type
            },
            message=f"Recommended {len(chart_suggestions)} visualization types",
            reasoning=reasoning,
            confidence=0.87,
            metadata={
                "task_type": "recommend_visualizations",
                "data_type": data_type
            }
        )

    async def _format_report(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Format report for specific output"""
        report_data = task.get("report_data", {})
        output_format = task.get("format", "markdown")

        reasoning = await self.think(
            f"Format report as {output_format}",
            {}
        )

        # Format based on output type
        if output_format == "markdown":
            formatted = self._format_as_markdown(report_data)
        elif output_format == "html":
            formatted = self._format_as_html(report_data)
        elif output_format == "json":
            formatted = self._format_as_json(report_data)
        else:
            formatted = str(report_data)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "formatted_report": formatted,
                "format": output_format,
                "size": len(formatted)
            },
            message=f"Report formatted as {output_format}",
            reasoning=reasoning,
            confidence=0.95,
            metadata={
                "task_type": "format_report",
                "format": output_format
            }
        )

    def _parse_report_sections(self, text: str) -> List[Dict[str, Any]]:
        """Parse report into sections"""
        sections = []
        current_section = None
        current_content = []

        for line in text.split('\n'):
            line = line.strip()

            # Check if it's a section header
            if line and (line.isupper() or line.endswith(':') or
                        any(line.startswith(num) for num in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'])):
                # Save previous section
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": "\n".join(current_content)
                    })

                # Start new section
                current_section = line.rstrip(':').strip()
                current_content = []
            elif line:
                current_content.append(line)

        # Save last section
        if current_section:
            sections.append({
                "title": current_section,
                "content": "\n".join(current_content)
            })

        return sections

    def _generate_report_metadata(
        self,
        topic: str,
        audience: str,
        template: str
    ) -> Dict[str, Any]:
        """Generate report metadata"""
        return {
            "title": f"Report: {topic}",
            "generated_at": datetime.now().isoformat(),
            "generated_by": "OmniSense Report Agent",
            "audience": audience,
            "template": template,
            "version": "1.0"
        }

    def _build_report_structure(
        self,
        topic: str,
        sections: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        template: str
    ) -> Dict[str, Any]:
        """Build complete report structure"""
        report = {
            "metadata": metadata,
            "title": f"Report: {topic}",
            "sections": sections,
            "generated_at": metadata["generated_at"]
        }

        # Add template-specific elements
        if template == "executive":
            report["format"] = "executive"
            report["page_limit"] = 2
        elif template == "technical":
            report["format"] = "technical"
            report["include_methodology"] = True
        else:
            report["format"] = "standard"

        return report

    def _extract_key_points(self, summary: str) -> List[str]:
        """Extract key points from summary"""
        key_points = []

        sentences = summary.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            # Key points often start with certain patterns
            if sentence and (
                any(sentence.startswith(word) for word in
                    ["Key", "Important", "Critical", "Notable", "Significant"]) or
                len(sentence.split()) > 10
            ):
                key_points.append(sentence)

        return key_points[:5]  # Top 5 key points

    def _parse_synthesized_insights(self, text: str) -> List[Dict[str, Any]]:
        """Parse synthesized insights"""
        insights = []

        for line in text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    # Categorize insight
                    category = "general"
                    if "trend" in content.lower():
                        category = "trend"
                    elif "recommend" in content.lower():
                        category = "recommendation"
                    elif "risk" in content.lower() or "concern" in content.lower():
                        category = "risk"

                    insights.append({
                        "insight": content,
                        "category": category
                    })

        return insights

    def _parse_visualization_recommendations(self, text: str) -> Dict[str, Any]:
        """Parse visualization recommendations"""
        recommendations = {
            "chart_types": [],
            "key_metrics": [],
            "styling": []
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "chart" in line_lower or "graph" in line_lower:
                current_section = "chart_types"
            elif "metric" in line_lower:
                current_section = "key_metrics"
            elif "style" in line_lower or "color" in line_lower:
                current_section = "styling"
            elif current_section and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    recommendations[current_section].append(content)

        return recommendations

    def _generate_chart_suggestions(
        self,
        data_type: str,
        data_size: str,
        story: str
    ) -> List[Dict[str, Any]]:
        """Generate specific chart suggestions"""
        suggestions = []

        # Based on data type
        if data_type == "time_series":
            suggestions.append({
                "type": "line_chart",
                "description": "Show trends over time",
                "priority": "high"
            })
            suggestions.append({
                "type": "area_chart",
                "description": "Show cumulative changes",
                "priority": "medium"
            })

        elif data_type == "categorical":
            suggestions.append({
                "type": "bar_chart",
                "description": "Compare categories",
                "priority": "high"
            })
            suggestions.append({
                "type": "pie_chart",
                "description": "Show proportions",
                "priority": "medium"
            })

        elif data_type == "hierarchical":
            suggestions.append({
                "type": "treemap",
                "description": "Show hierarchical relationships",
                "priority": "high"
            })
            suggestions.append({
                "type": "sunburst",
                "description": "Show nested hierarchies",
                "priority": "medium"
            })

        elif data_type == "comparison":
            suggestions.append({
                "type": "grouped_bar",
                "description": "Compare multiple series",
                "priority": "high"
            })
            suggestions.append({
                "type": "radar_chart",
                "description": "Multi-dimensional comparison",
                "priority": "medium"
            })

        elif data_type == "distribution":
            suggestions.append({
                "type": "histogram",
                "description": "Show data distribution",
                "priority": "high"
            })
            suggestions.append({
                "type": "box_plot",
                "description": "Show statistical distribution",
                "priority": "medium"
            })

        else:  # mixed or general
            suggestions.append({
                "type": "dashboard",
                "description": "Multi-chart overview",
                "priority": "high"
            })

        # Consider data size
        if data_size == "large":
            suggestions.append({
                "type": "heatmap",
                "description": "Visualize large datasets",
                "priority": "high"
            })

        return suggestions

    def _format_as_markdown(self, report_data: Dict[str, Any]) -> str:
        """Format report as Markdown"""
        lines = []

        # Title
        title = report_data.get("title", "Report")
        lines.append(f"# {title}\n")

        # Metadata
        metadata = report_data.get("metadata", {})
        if metadata:
            lines.append("## Metadata")
            lines.append(f"- Generated: {metadata.get('generated_at', 'N/A')}")
            lines.append(f"- Generated by: {metadata.get('generated_by', 'N/A')}")
            lines.append(f"- Audience: {metadata.get('audience', 'N/A')}\n")

        # Sections
        sections = report_data.get("sections", [])
        for section in sections:
            lines.append(f"## {section.get('title', 'Section')}\n")
            lines.append(section.get('content', '') + "\n")

        return "\n".join(lines)

    def _format_as_html(self, report_data: Dict[str, Any]) -> str:
        """Format report as HTML"""
        title = report_data.get("title", "Report")
        sections = report_data.get("sections", [])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""

        # Metadata
        metadata = report_data.get("metadata", {})
        if metadata:
            html += '    <div class="metadata">\n'
            html += f'        <p><strong>Generated:</strong> {metadata.get("generated_at", "N/A")}</p>\n'
            html += f'        <p><strong>Generated by:</strong> {metadata.get("generated_by", "N/A")}</p>\n'
            html += '    </div>\n'

        # Sections
        for section in sections:
            html += f'    <h2>{section.get("title", "Section")}</h2>\n'
            html += f'    <p>{section.get("content", "").replace(chr(10), "<br>")}</p>\n'

        html += """</body>
</html>"""

        return html

    def _format_as_json(self, report_data: Dict[str, Any]) -> str:
        """Format report as JSON"""
        import json
        return json.dumps(report_data, indent=2, ensure_ascii=False)
