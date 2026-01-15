"""
Academic Agent - Research and Scholarly Analysis
负责学术研究、论文分析和知识图谱构建
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole, AgentResponse, AgentState


class AcademicAgent(BaseAgent):
    """
    Academic agent for research and scholarly analysis

    Capabilities:
    - Literature review and synthesis
    - Research paper analysis
    - Citation analysis
    - Research trend identification
    - Knowledge graph construction
    - Research gap identification
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Academic",
                role=AgentRole.ACADEMIC,
                system_prompt=self._get_system_prompt()
            )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are an Academic Agent specialized in research and scholarly analysis.

Your role:
1. Analyze research papers and academic content
2. Conduct literature reviews and synthesis
3. Identify research trends and gaps
4. Analyze citations and academic impact
5. Extract key research findings
6. Build knowledge graphs and connections

Approach:
- Maintain academic rigor and accuracy
- Cite sources and evidence
- Identify methodological considerations
- Consider theoretical frameworks
- Evaluate research quality
- Synthesize across multiple sources

Output format:
Always provide structured academic analysis:
{
  "summary": "...",
  "key_findings": [...],
  "methodology": "...",
  "contributions": [...],
  "limitations": [...],
  "future_research": [...],
  "citations": [...]
}
"""

    def _setup_chains(self):
        """Setup LangChain chains for academic operations"""
        # Literature review chain
        self._create_chain(
            name="literature_review",
            template="""
Conduct a literature review on the following papers:

Papers: {papers}
Topic: {topic}
Focus Areas: {focus_areas}

Provide comprehensive review:
1. Overview of the research area
2. Key themes and trends
3. Seminal works and contributions
4. Methodological approaches
5. Research gaps identified
6. Synthesis and conclusions

Literature Review:
""",
            input_variables=["papers", "topic", "focus_areas"]
        )

        # Paper analysis chain
        self._create_chain(
            name="paper_analysis",
            template="""
Analyze the following research paper:

Title: {title}
Authors: {authors}
Abstract: {abstract}
Content: {content}

Provide detailed analysis:
1. Research question and objectives
2. Methodology and approach
3. Key findings and results
4. Contributions to the field
5. Limitations and weaknesses
6. Implications and future work

Paper Analysis:
""",
            input_variables=["title", "authors", "abstract", "content"]
        )

        # Citation analysis chain
        self._create_chain(
            name="citation_analysis",
            template="""
Analyze citation patterns:

Paper: {paper_title}
Citations: {citations}
Cited By: {cited_by}

Analyze:
1. Citation impact and influence
2. Key citing papers
3. Citation trends over time
4. Research communities citing this work
5. Impact metrics interpretation
6. Academic influence assessment

Citation Analysis:
""",
            input_variables=["paper_title", "citations", "cited_by"]
        )

        # Research gap identification chain
        self._create_chain(
            name="gap_identification",
            template="""
Identify research gaps in the following area:

Research Area: {research_area}
Existing Literature: {literature}
Current State: {current_state}

Identify:
1. Unexplored questions
2. Methodological gaps
3. Theoretical gaps
4. Empirical gaps
5. Interdisciplinary opportunities
6. Emerging research directions

Research Gaps:
""",
            input_variables=["research_area", "literature", "current_state"]
        )

    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process academic task

        Task types:
        - literature_review: Conduct literature review
        - paper_analysis: Analyze research paper
        - citation_analysis: Analyze citations
        - trend_analysis: Identify research trends
        - gap_identification: Identify research gaps
        - knowledge_graph: Build knowledge graph
        """
        self.state = AgentState.WORKING
        context = context or {}

        try:
            task_type = task.get("type", "paper_analysis")

            if task_type == "literature_review":
                result = await self._literature_review(task, context)
            elif task_type == "paper_analysis":
                result = await self._paper_analysis(task, context)
            elif task_type == "citation_analysis":
                result = await self._citation_analysis(task, context)
            elif task_type == "trend_analysis":
                result = await self._trend_analysis(task, context)
            elif task_type == "gap_identification":
                result = await self._gap_identification(task, context)
            elif task_type == "knowledge_graph":
                result = await self._knowledge_graph(task, context)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            logger.error(f"Academic processing failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def _literature_review(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Conduct literature review"""
        papers = task.get("papers", [])
        topic = task.get("topic", "")
        focus_areas = task.get("focus_areas", [])

        reasoning = await self.think(
            f"Conduct literature review on {topic}",
            {"paper_count": len(papers), "focus_areas": focus_areas}
        )

        # Run literature review chain
        chain_result = await self._execute_with_retry(
            self.chains["literature_review"].ainvoke,
            {
                "papers": str(papers)[:4000],
                "topic": topic,
                "focus_areas": str(focus_areas)
            }
        )

        # Parse review
        review = self._parse_literature_review(chain_result["text"])

        # Extract key themes
        themes = self._extract_themes(papers)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "topic": topic,
                "review": review,
                "themes": themes,
                "paper_count": len(papers)
            },
            message=f"Literature review completed on {topic} ({len(papers)} papers)",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "literature_review",
                "topic": topic
            }
        )

    async def _paper_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze research paper"""
        title = task.get("title", "")
        authors = task.get("authors", [])
        abstract = task.get("abstract", "")
        content = task.get("content", "")

        reasoning = await self.think(
            f"Analyze paper: {title}",
            {"has_content": len(content) > 0}
        )

        # Run paper analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["paper_analysis"].ainvoke,
            {
                "title": title,
                "authors": str(authors),
                "abstract": abstract[:1000],
                "content": content[:3000]
            }
        )

        # Parse analysis
        analysis = self._parse_paper_analysis(chain_result["text"])

        # Extract key concepts
        concepts = self._extract_concepts(abstract + " " + content[:2000])

        # Calculate paper quality score
        quality_score = self._calculate_paper_quality(
            title, authors, abstract, content
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "title": title,
                "authors": authors,
                "analysis": analysis,
                "concepts": concepts,
                "quality_score": quality_score
            },
            message=f"Paper analysis completed: {title} (quality: {quality_score}/100)",
            reasoning=reasoning,
            confidence=0.88,
            metadata={
                "task_type": "paper_analysis",
                "title": title
            }
        )

    async def _citation_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze citations"""
        paper_title = task.get("paper_title", "")
        citations = task.get("citations", [])
        cited_by = task.get("cited_by", [])

        reasoning = await self.think(
            f"Analyze citations for {paper_title}",
            {"citations": len(citations), "cited_by": len(cited_by)}
        )

        # Run citation analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["citation_analysis"].ainvoke,
            {
                "paper_title": paper_title,
                "citations": str(citations)[:2000],
                "cited_by": str(cited_by)[:2000]
            }
        )

        # Parse citation analysis
        citation_analysis = self._parse_citation_analysis(chain_result["text"])

        # Calculate impact metrics
        impact_metrics = self._calculate_impact_metrics(citations, cited_by)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "paper_title": paper_title,
                "citation_analysis": citation_analysis,
                "impact_metrics": impact_metrics,
                "citation_count": len(citations),
                "cited_by_count": len(cited_by)
            },
            message=f"Citation analysis: {len(citations)} citations, "
                    f"{len(cited_by)} citing papers (h-index approx: {impact_metrics.get('h_index', 0)})",
            reasoning=reasoning,
            confidence=0.82,
            metadata={
                "task_type": "citation_analysis"
            }
        )

    async def _trend_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze research trends"""
        research_area = task.get("research_area", "")
        papers = task.get("papers", [])
        timeframe = task.get("timeframe", "recent")

        reasoning = await self.think(
            f"Analyze trends in {research_area}",
            {"paper_count": len(papers), "timeframe": timeframe}
        )

        # Identify trends
        trends = self._identify_research_trends(papers)

        # Identify emerging topics
        emerging_topics = self._identify_emerging_topics(papers)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "research_area": research_area,
                "trends": trends,
                "emerging_topics": emerging_topics,
                "timeframe": timeframe
            },
            message=f"Identified {len(trends)} trends and {len(emerging_topics)} "
                    f"emerging topics in {research_area}",
            reasoning=reasoning,
            confidence=0.78,
            metadata={
                "task_type": "trend_analysis",
                "research_area": research_area
            }
        )

    async def _gap_identification(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Identify research gaps"""
        research_area = task.get("research_area", "")
        literature = task.get("literature", [])
        current_state = task.get("current_state", "")

        reasoning = await self.think(
            f"Identify gaps in {research_area}",
            {"literature_count": len(literature)}
        )

        # Run gap identification chain
        chain_result = await self._execute_with_retry(
            self.chains["gap_identification"].ainvoke,
            {
                "research_area": research_area,
                "literature": str(literature)[:3000],
                "current_state": current_state[:1000]
            }
        )

        # Parse gaps
        gaps = self._parse_research_gaps(chain_result["text"])

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "research_area": research_area,
                "gaps": gaps,
                "gap_count": len(gaps)
            },
            message=f"Identified {len(gaps)} research gaps in {research_area}",
            reasoning=reasoning,
            confidence=0.75,
            metadata={
                "task_type": "gap_identification",
                "research_area": research_area
            }
        )

    async def _knowledge_graph(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Build knowledge graph"""
        papers = task.get("papers", [])
        focus = task.get("focus", "concepts")

        reasoning = await self.think(
            f"Build knowledge graph from {len(papers)} papers",
            {"focus": focus}
        )

        # Extract entities and relationships
        entities = self._extract_entities(papers)
        relationships = self._extract_relationships(papers)

        # Build graph structure
        graph = self._build_graph_structure(entities, relationships)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "graph": graph,
                "entity_count": len(entities),
                "relationship_count": len(relationships),
                "focus": focus
            },
            message=f"Built knowledge graph with {len(entities)} entities "
                    f"and {len(relationships)} relationships",
            reasoning=reasoning,
            confidence=0.8,
            metadata={
                "task_type": "knowledge_graph",
                "focus": focus
            }
        )

    def _parse_literature_review(self, text: str) -> Dict[str, Any]:
        """Parse literature review results"""
        review = {
            "overview": "",
            "key_themes": [],
            "gaps": []
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "overview" in line_lower:
                current_section = "overview"
            elif "theme" in line_lower:
                current_section = "key_themes"
            elif "gap" in line_lower:
                current_section = "gaps"
            elif current_section:
                if current_section == "overview":
                    review["overview"] += line + " "
                elif line[0].isdigit() or line.startswith(('-', '•')):
                    content = line.lstrip('0123456789.-• ').strip()
                    if content:
                        review[current_section].append(content)

        return review

    def _parse_paper_analysis(self, text: str) -> Dict[str, Any]:
        """Parse paper analysis results"""
        analysis = {
            "research_question": "",
            "methodology": "",
            "key_findings": [],
            "contributions": [],
            "limitations": []
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "research question" in line_lower or "objective" in line_lower:
                current_section = "research_question"
            elif "methodology" in line_lower or "method" in line_lower:
                current_section = "methodology"
            elif "finding" in line_lower or "result" in line_lower:
                current_section = "key_findings"
            elif "contribution" in line_lower:
                current_section = "contributions"
            elif "limitation" in line_lower:
                current_section = "limitations"
            elif current_section:
                if current_section in ["research_question", "methodology"]:
                    analysis[current_section] += line + " "
                elif line[0].isdigit() or line.startswith(('-', '•')):
                    content = line.lstrip('0123456789.-• ').strip()
                    if content:
                        analysis[current_section].append(content)

        return analysis

    def _parse_citation_analysis(self, text: str) -> Dict[str, Any]:
        """Parse citation analysis results"""
        analysis = {
            "impact_assessment": "moderate",
            "key_citing_papers": [],
            "trends": []
        }

        text_lower = text.lower()
        if "high impact" in text_lower or "significant influence" in text_lower:
            analysis["impact_assessment"] = "high"
        elif "low impact" in text_lower or "limited influence" in text_lower:
            analysis["impact_assessment"] = "low"

        return analysis

    def _parse_research_gaps(self, text: str) -> List[Dict[str, Any]]:
        """Parse research gaps"""
        gaps = []

        for line in text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    gap_type = "theoretical"
                    if "empirical" in content.lower():
                        gap_type = "empirical"
                    elif "method" in content.lower():
                        gap_type = "methodological"

                    gaps.append({
                        "description": content,
                        "type": gap_type
                    })

        return gaps

    def _extract_themes(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract key themes from papers"""
        themes = {}

        for paper in papers:
            # Extract from title and abstract
            text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
            words = text.split()

            # Simple keyword extraction
            for word in words:
                if len(word) > 4 and word.isalpha():
                    themes[word] = themes.get(word, 0) + 1

        # Sort by frequency
        sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)

        return [
            {"theme": theme, "frequency": freq}
            for theme, freq in sorted_themes[:10]
        ]

    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        # Simple concept extraction using capitalized phrases
        concepts = []
        words = text.split()

        for i, word in enumerate(words):
            if word and word[0].isupper() and len(word) > 3:
                # Check if next word is also capitalized (multi-word concept)
                concept = word
                j = i + 1
                while j < len(words) and words[j] and words[j][0].isupper():
                    concept += " " + words[j]
                    j += 1

                if concept not in concepts:
                    concepts.append(concept)

        return concepts[:20]

    def _calculate_paper_quality(
        self,
        title: str,
        authors: List[str],
        abstract: str,
        content: str
    ) -> int:
        """Calculate paper quality score"""
        score = 50  # Base score

        # Title quality (0-10 points)
        if title and len(title.split()) >= 5:
            score += 10

        # Author count (0-10 points)
        score += min(10, len(authors) * 2)

        # Abstract quality (0-15 points)
        if abstract and len(abstract) > 100:
            score += 15

        # Content quality (0-15 points)
        if content and len(content) > 1000:
            score += 15

        return min(100, score)

    def _calculate_impact_metrics(
        self,
        citations: List[Any],
        cited_by: List[Any]
    ) -> Dict[str, Any]:
        """Calculate impact metrics"""
        metrics = {
            "citation_count": len(citations),
            "cited_by_count": len(cited_by),
            "h_index": 0
        }

        # Simple h-index approximation
        if cited_by:
            citation_counts = sorted(
                [len(cited_by)],
                reverse=True
            )
            h_index = 0
            for i, count in enumerate(citation_counts, 1):
                if count >= i:
                    h_index = i
                else:
                    break
            metrics["h_index"] = h_index

        return metrics

    def _identify_research_trends(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify research trends"""
        trends = []

        # Group by year if available
        year_groups = {}
        for paper in papers:
            year = paper.get("year", "unknown")
            if year not in year_groups:
                year_groups[year] = []
            year_groups[year].append(paper)

        # Analyze trend
        if len(year_groups) > 1:
            trends.append({
                "trend": "Growing research interest",
                "evidence": f"Papers published across {len(year_groups)} years"
            })

        return trends

    def _identify_emerging_topics(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Identify emerging topics"""
        # Extract recent keywords
        recent_keywords = {}

        for paper in papers:
            keywords = paper.get("keywords", [])
            for keyword in keywords:
                recent_keywords[keyword] = recent_keywords.get(keyword, 0) + 1

        # Sort by frequency
        sorted_keywords = sorted(
            recent_keywords.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [kw for kw, _ in sorted_keywords[:10]]

    def _extract_entities(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract entities from papers"""
        entities = []

        for paper in papers:
            # Authors as entities
            for author in paper.get("authors", []):
                entities.append({
                    "id": f"author_{author}",
                    "type": "author",
                    "name": author
                })

            # Paper as entity
            entities.append({
                "id": f"paper_{paper.get('id', len(entities))}",
                "type": "paper",
                "name": paper.get("title", "Unknown")
            })

        return entities

    def _extract_relationships(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        relationships = []

        for paper in papers:
            paper_id = f"paper_{paper.get('id', 0)}"

            # Author-paper relationships
            for author in paper.get("authors", []):
                relationships.append({
                    "source": f"author_{author}",
                    "target": paper_id,
                    "type": "authored"
                })

            # Citation relationships
            for citation in paper.get("citations", []):
                relationships.append({
                    "source": paper_id,
                    "target": f"paper_{citation}",
                    "type": "cites"
                })

        return relationships

    def _build_graph_structure(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build graph structure"""
        return {
            "nodes": entities,
            "edges": relationships,
            "metadata": {
                "node_count": len(entities),
                "edge_count": len(relationships)
            }
        }
