# OmniSense Multi-Agent System

Complete multi-agent system for intelligent data analysis and content generation.

## Architecture Overview

The OmniSense multi-agent system follows the BettaFish architecture pattern with specialized agents that collaborate to perform complex tasks.

### Agent Hierarchy

```
AgentManager (Orchestrator)
    ├── ScoutAgent (Data Explorer)
    ├── AnalystAgent (Deep Analyzer)
    ├── EcommerceAgent (Product Specialist)
    ├── AcademicAgent (Research Specialist)
    ├── CreatorAgent (Content Creator)
    └── ReportAgent (Document Generator)
```

## Agents

### 1. BaseAgent
**Location**: `omnisense/agents/base.py`

Foundation class providing:
- LangChain integration (Ollama, OpenAI, Anthropic)
- Chain-of-thought reasoning
- Async operations
- Conversation memory
- Error handling with retry logic
- Structured output generation

### 2. ScoutAgent
**Location**: `omnisense/agents/scout.py`

**Capabilities**:
- Platform content discovery
- Trend identification
- Keyword extraction
- Data quality assessment
- Quick insights generation

**Task Types**:
- `discover`: Explore and discover content
- `analyze_trends`: Identify trends
- `extract_keywords`: Extract keywords
- `assess_quality`: Assess data quality

**Example**:
```python
scout = ScoutAgent()
result = await scout.process({
    "type": "discover",
    "data": [...],
    "platform": "douyin"
})
```

### 3. AnalystAgent
**Location**: `omnisense/agents/analyst.py`

**Capabilities**:
- Statistical analysis
- Sentiment analysis
- Pattern recognition
- Correlation analysis
- Predictive insights
- Comparative analysis

**Task Types**:
- `deep_analysis`: Comprehensive analysis
- `sentiment_analysis`: Sentiment analysis
- `pattern_recognition`: Pattern identification
- `comparative_analysis`: Compare datasets
- `statistical_analysis`: Statistical analysis

**Example**:
```python
analyst = AnalystAgent()
result = await analyst.process({
    "type": "sentiment_analysis",
    "content": "Product review text...",
    "platform": "amazon"
})
```

### 4. EcommerceAgent
**Location**: `omnisense/agents/ecommerce.py`

**Capabilities**:
- Product analysis and comparison
- Price analysis and trends
- Review and rating analysis
- Competitor analysis
- Market positioning
- Purchase recommendations

**Task Types**:
- `product_analysis`: Analyze a product
- `price_analysis`: Analyze pricing
- `review_analysis`: Analyze reviews
- `competitive_analysis`: Competitive analysis
- `market_analysis`: Market analysis
- `purchase_recommendation`: Purchase recommendation

**Example**:
```python
ecommerce = EcommerceAgent()
result = await ecommerce.process({
    "type": "product_analysis",
    "product_name": "Smartphone X",
    "platform": "amazon",
    "details": {...},
    "reviews": [...]
})
```

### 5. AcademicAgent
**Location**: `omnisense/agents/academic.py`

**Capabilities**:
- Literature review and synthesis
- Research paper analysis
- Citation analysis
- Research trend identification
- Knowledge graph construction
- Research gap identification

**Task Types**:
- `literature_review`: Conduct literature review
- `paper_analysis`: Analyze research paper
- `citation_analysis`: Analyze citations
- `trend_analysis`: Identify research trends
- `gap_identification`: Identify research gaps
- `knowledge_graph`: Build knowledge graph

**Example**:
```python
academic = AcademicAgent()
result = await academic.process({
    "type": "paper_analysis",
    "title": "Paper title",
    "authors": [...],
    "abstract": "...",
    "content": "..."
})
```

### 6. CreatorAgent
**Location**: `omnisense/agents/creator.py`

**Capabilities**:
- Content generation and optimization
- Platform-specific recommendations
- SEO and engagement optimization
- Content strategy development
- Hashtag and keyword suggestions
- Viral content analysis

**Task Types**:
- `generate_content`: Generate new content
- `optimize_content`: Optimize existing content
- `suggest_hashtags`: Suggest hashtags
- `content_strategy`: Develop content strategy
- `analyze_viral`: Analyze viral content
- `platform_adaptation`: Adapt content for platforms

**Example**:
```python
creator = CreatorAgent()
result = await creator.process({
    "type": "generate_content",
    "topic": "Sustainable living",
    "platform": "xiaohongshu",
    "audience": "millennials",
    "tone": "friendly"
})
```

### 7. ReportAgent
**Location**: `omnisense/agents/report.py`

**Capabilities**:
- Comprehensive report generation
- Executive summary creation
- Data visualization recommendations
- Multi-format export (PDF, HTML, Markdown)
- Template-based reporting
- Automated insight summarization

**Task Types**:
- `generate_report`: Generate comprehensive report
- `executive_summary`: Create executive summary
- `synthesize_insights`: Synthesize insights
- `recommend_visualizations`: Recommend charts/graphs
- `format_report`: Format report for specific output

**Example**:
```python
report = ReportAgent()
result = await report.process({
    "type": "generate_report",
    "topic": "Market Analysis Q1 2024",
    "data": {...},
    "analysis": {...},
    "audience": "executives"
})
```

### 8. AgentManager
**Location**: `omnisense/agents/manager.py`

**Capabilities**:
- Agent lifecycle management
- Task distribution and scheduling
- Agent collaboration coordination
- Resource management
- Result aggregation
- Performance tracking

**Features**:
- Task dependencies
- Priority-based scheduling
- Concurrent execution with limits
- Workflow orchestration
- Multi-agent collaboration
- Metrics and monitoring

**Example**:
```python
manager = AgentManager()
manager.register_agent(ScoutAgent())
manager.register_agent(AnalystAgent())

# Submit task
task_id = await manager.submit_task(
    agent_role=AgentRole.SCOUT,
    parameters={...},
    priority="high"
)

# Run all tasks
results = await manager.run_all_tasks(max_concurrent=5)
```

## Usage Patterns

### Pattern 1: Single Agent
```python
agent = ScoutAgent()
result = await agent.process(task, context)
```

### Pattern 2: Agent Collaboration
```python
scout = ScoutAgent()
analyst = AnalystAgent()
result = await scout.collaborate(analyst, task)
```

### Pattern 3: Manager Orchestration
```python
manager = AgentManager()
manager.register_agent(ScoutAgent())
manager.register_agent(AnalystAgent())

task_id = await manager.submit_task(...)
results = await manager.run_all_tasks()
```

### Pattern 4: Workflow Execution
```python
workflow = [
    {"role": AgentRole.SCOUT, "parameters": {...}, "depends_on": []},
    {"role": AgentRole.ANALYST, "parameters": {...}, "depends_on": [0]},
    {"role": AgentRole.REPORT, "parameters": {...}, "depends_on": [0, 1]}
]

results = await manager.orchestrate_workflow(workflow)
```

### Pattern 5: Multi-Agent Collaboration
```python
agents = [scout, analyst, ecommerce]
result = await manager.collaborate_agents(agents, task, context)
```

## Configuration

### LLM Configuration

Configure LLM providers in `omnisense/config.py`:

```python
class AgentConfig(BaseSettings):
    llm_provider: str = "ollama"  # ollama, openai, anthropic
    llm_model: str = "qwen2.5:7b"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
```

### Environment Variables

Create `.env` file:
```bash
# LLM Configuration
AGENT__LLM_PROVIDER=ollama
AGENT__LLM_MODEL=qwen2.5:7b
AGENT__OLLAMA_BASE_URL=http://localhost:11434

# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...
```

## Features

### Chain-of-Thought Reasoning
All agents support chain-of-thought reasoning for transparent decision-making:

```python
reasoning = await agent.think(query, context)
# Returns step-by-step reasoning process
```

### Structured Outputs
Agents return standardized `AgentResponse` objects:

```python
class AgentResponse(BaseModel):
    agent_name: str
    agent_role: AgentRole
    success: bool
    data: Optional[Dict[str, Any]]
    message: str
    reasoning: List[str]  # Chain of thought
    confidence: float
    metadata: Dict[str, Any]
    timestamp: datetime
    error: Optional[str]
```

### Error Handling
Built-in retry logic with exponential backoff:

```python
result = await agent._execute_with_retry(
    func,
    *args,
    max_retries=3,
    **kwargs
)
```

### Async Support
All operations are async for high performance:

```python
# Concurrent task execution
results = await asyncio.gather(*[
    agent1.process(task1),
    agent2.process(task2),
    agent3.process(task3)
])
```

### Memory Management
Agents maintain conversation memory:

```python
agent = ScoutAgent(config=AgentConfig(enable_memory=True))
# Agent remembers conversation context
```

## Performance

### Concurrency Control
```python
# Limit concurrent tasks
results = await manager.run_all_tasks(max_concurrent=5)
```

### Task Dependencies
```python
# Task B waits for Task A to complete
task_a = await manager.submit_task(...)
task_b = await manager.submit_task(..., dependencies=[task_a])
```

### Metrics Tracking
```python
metrics = manager.get_metrics()
# Returns:
# - Task counts (total, completed, failed)
# - Agent performance metrics
# - Execution times
# - Confidence scores
```

## Examples

See `examples/multi_agent_examples.py` for comprehensive examples:

1. Basic agent usage
2. Agent collaboration
3. Agent manager orchestration
4. E-commerce analysis workflow
5. Academic research workflow
6. Content creation workflow
7. Complete analysis pipeline
8. Report generation

Run examples:
```bash
python examples/multi_agent_examples.py
```

## Integration with OmniSense

The multi-agent system integrates seamlessly with OmniSense components:

### With Spider System
```python
# Spider collects data -> Scout explores -> Analyst analyzes
spider_data = await spider.crawl(platform)
scout_result = await scout.process({"type": "discover", "data": spider_data})
analyst_result = await analyst.process({"type": "deep_analysis", "data": scout_result.data})
```

### With Storage
```python
# Store agent results in database
from omnisense.storage import DatabaseManager

db = DatabaseManager()
await db.store_agent_result(result)
```

### With Visualization
```python
# Generate report with visualizations
report_result = await report.process({
    "type": "generate_report",
    "topic": "Analysis Report",
    "data": analysis_data
})

# Visualize recommendations
viz_result = await report.process({
    "type": "recommend_visualizations",
    "data_type": "time_series",
    "story": "Show growth trends"
})
```

## Best Practices

### 1. Agent Selection
- Use **ScoutAgent** for initial exploration
- Use **AnalystAgent** for deep analysis
- Use **EcommerceAgent** for product/market analysis
- Use **AcademicAgent** for research tasks
- Use **CreatorAgent** for content generation
- Use **ReportAgent** for final reporting

### 2. Task Design
- Keep tasks focused and specific
- Provide sufficient context
- Use appropriate task types
- Set realistic confidence thresholds

### 3. Workflow Design
- Start with scout/discovery
- Progress to analysis
- End with reporting
- Use dependencies for sequential tasks
- Run independent tasks concurrently

### 4. Error Handling
- Always check `result.success`
- Handle errors gracefully
- Use retry logic for transient failures
- Log errors for debugging

### 5. Performance
- Use `max_concurrent` to control resources
- Profile agent performance
- Monitor confidence scores
- Optimize chain prompts

## Troubleshooting

### LLM Connection Issues
```python
# Check LLM availability
from langchain_community.llms import Ollama
llm = Ollama(model="qwen2.5:7b")
response = llm.invoke("Hello")
```

### Memory Issues
```python
# Reset agent memory
agent.reset()
```

### Task Failures
```python
# Check task status
task = manager.tasks[task_id]
print(f"Status: {task.status}")
print(f"Error: {task.result.error if task.result else None}")
```

## Future Enhancements

- [ ] Add more specialized agents (Video, Audio, Image)
- [ ] Implement agent learning from feedback
- [ ] Add agent performance optimization
- [ ] Implement distributed agent execution
- [ ] Add agent communication protocols
- [ ] Implement agent personality/style customization
- [ ] Add agent capability discovery
- [ ] Implement dynamic agent composition

## Contributing

When adding new agents:

1. Inherit from `BaseAgent`
2. Implement `_get_system_prompt()`
3. Implement `_setup_chains()`
4. Implement `process()` method
5. Add comprehensive docstrings
6. Add unit tests
7. Update documentation

## License

MIT License - See LICENSE file for details
