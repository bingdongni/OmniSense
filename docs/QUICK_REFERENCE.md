# OmniSense Multi-Agent System - Quick Reference

## Quick Start

### 1. Import Agents
```python
from omnisense.agents import (
    AgentManager,
    ScoutAgent,
    AnalystAgent,
    EcommerceAgent,
    AcademicAgent,
    CreatorAgent,
    ReportAgent
)
```

### 2. Create and Use Single Agent
```python
import asyncio

async def main():
    # Create agent
    scout = ScoutAgent()

    # Process task
    result = await scout.process({
        "type": "discover",
        "data": [...],
        "platform": "douyin"
    })

    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Data: {result.data}")

asyncio.run(main())
```

### 3. Use Agent Manager
```python
async def main():
    # Create manager
    manager = AgentManager()

    # Register agents
    manager.register_agent(ScoutAgent())
    manager.register_agent(AnalystAgent())

    # Submit task
    from omnisense.agents import AgentRole

    task_id = await manager.submit_task(
        agent_role=AgentRole.SCOUT,
        parameters={"type": "discover", "data": [...]},
        priority="high"
    )

    # Run tasks
    results = await manager.run_all_tasks()

    for result in results:
        print(result.message)

asyncio.run(main())
```

## Agent Quick Reference

### ScoutAgent - Data Explorer
```python
scout = ScoutAgent()

# Discover content
await scout.process({
    "type": "discover",
    "data": [...],
    "platform": "douyin"
})

# Analyze trends
await scout.process({
    "type": "analyze_trends",
    "data": [...],
    "timeframe": "recent"
})

# Extract keywords
await scout.process({
    "type": "extract_keywords",
    "content": "...",
    "language": "zh"
})

# Assess quality
await scout.process({
    "type": "assess_quality",
    "data": [...]
})
```

### AnalystAgent - Deep Analyzer
```python
analyst = AnalystAgent()

# Deep analysis
await analyst.process({
    "type": "deep_analysis",
    "data": [...],
    "analysis_type": "general"
})

# Sentiment analysis
await analyst.process({
    "type": "sentiment_analysis",
    "content": "...",
    "platform": "weibo"
})

# Pattern recognition
await analyst.process({
    "type": "pattern_recognition",
    "data": [...],
    "timeframe": "monthly"
})

# Comparative analysis
await analyst.process({
    "type": "comparative_analysis",
    "dataset_a": [...],
    "dataset_b": [...]
})
```

### EcommerceAgent - Product Specialist
```python
ecommerce = EcommerceAgent()

# Product analysis
await ecommerce.process({
    "type": "product_analysis",
    "product_name": "...",
    "platform": "amazon",
    "details": {...},
    "reviews": [...]
})

# Price analysis
await ecommerce.process({
    "type": "price_analysis",
    "product_name": "...",
    "current_price": 999,
    "price_history": [...],
    "competitor_prices": [...]
})

# Purchase recommendation
await ecommerce.process({
    "type": "purchase_recommendation",
    "products": [...],
    "preferences": {...},
    "budget": 1000
})
```

### AcademicAgent - Research Specialist
```python
academic = AcademicAgent()

# Paper analysis
await academic.process({
    "type": "paper_analysis",
    "title": "...",
    "authors": [...],
    "abstract": "...",
    "content": "..."
})

# Literature review
await academic.process({
    "type": "literature_review",
    "papers": [...],
    "topic": "...",
    "focus_areas": [...]
})

# Citation analysis
await academic.process({
    "type": "citation_analysis",
    "paper_title": "...",
    "citations": [...],
    "cited_by": [...]
})
```

### CreatorAgent - Content Creator
```python
creator = CreatorAgent()

# Generate content
await creator.process({
    "type": "generate_content",
    "topic": "...",
    "platform": "xiaohongshu",
    "audience": "millennials",
    "tone": "friendly"
})

# Optimize content
await creator.process({
    "type": "optimize_content",
    "content": "...",
    "platform": "instagram",
    "goal": "engagement"
})

# Suggest hashtags
await creator.process({
    "type": "suggest_hashtags",
    "content": "...",
    "platform": "tiktok",
    "niche": "lifestyle"
})
```

### ReportAgent - Document Generator
```python
report = ReportAgent()

# Generate report
await report.process({
    "type": "generate_report",
    "topic": "...",
    "data": {...},
    "analysis": {...},
    "audience": "executives"
})

# Executive summary
await report.process({
    "type": "executive_summary",
    "analysis": {...},
    "findings": [...]
})

# Format report
await report.process({
    "type": "format_report",
    "report_data": {...},
    "format": "markdown"  # or "html", "json"
})
```

## Common Patterns

### Pattern 1: Sequential Analysis
```python
# Scout → Analyst → Report
scout_result = await scout.process({"type": "discover", ...})
analyst_result = await analyst.process({"type": "deep_analysis", "data": scout_result.data})
report_result = await report.process({"type": "generate_report", "analysis": analyst_result.data})
```

### Pattern 2: Parallel Analysis
```python
# Multiple agents analyze same data
results = await asyncio.gather(
    scout.process({...}),
    analyst.process({...}),
    ecommerce.process({...})
)
```

### Pattern 3: Agent Collaboration
```python
# Two agents collaborate
result = await scout.collaborate(analyst, task)
```

### Pattern 4: Workflow Orchestration
```python
workflow = [
    {"role": AgentRole.SCOUT, "parameters": {...}, "depends_on": []},
    {"role": AgentRole.ANALYST, "parameters": {...}, "depends_on": [0]},
    {"role": AgentRole.REPORT, "parameters": {...}, "depends_on": [1]}
]
results = await manager.orchestrate_workflow(workflow)
```

## Configuration

### Default Configuration
```python
from omnisense.agents import AgentConfig

config = AgentConfig(
    name="MyAgent",
    role=AgentRole.SCOUT,
    llm_provider="ollama",      # or "openai", "anthropic"
    llm_model="qwen2.5:7b",     # or "gpt-4", "claude-3"
    temperature=0.7,
    max_tokens=4096,
    enable_memory=True,
    enable_cot=True             # Chain of thought
)

agent = ScoutAgent(config)
```

### Environment Variables
```bash
# .env file
AGENT__LLM_PROVIDER=ollama
AGENT__LLM_MODEL=qwen2.5:7b
AGENT__OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Response Structure

### AgentResponse
```python
result = await agent.process(...)

# Access response
result.success          # bool: Task success
result.message         # str: Human-readable message
result.data           # dict: Result data
result.reasoning      # list: Chain of thought steps
result.confidence     # float: 0-1 confidence score
result.metadata       # dict: Additional metadata
result.timestamp      # datetime: When completed
result.error          # str: Error message if failed
```

## Error Handling

```python
try:
    result = await agent.process(task)
    if result.success:
        print(f"Success: {result.message}")
    else:
        print(f"Failed: {result.error}")
except Exception as e:
    print(f"Exception: {e}")
```

## Testing

### Quick Test
```bash
python tests/test_agents_quick.py
```

### Run Examples
```bash
python examples/multi_agent_examples.py
```

## Tips

1. **Use appropriate agent for task**
   - Scout: Initial exploration
   - Analyst: Deep analysis
   - Ecommerce: Product/market
   - Academic: Research
   - Creator: Content
   - Report: Documentation

2. **Enable memory for conversations**
   ```python
   config = AgentConfig(enable_memory=True)
   ```

3. **Use chain-of-thought for transparency**
   ```python
   reasoning = result.reasoning
   for step in reasoning:
       print(f"- {step}")
   ```

4. **Control concurrency**
   ```python
   results = await manager.run_all_tasks(max_concurrent=5)
   ```

5. **Check confidence scores**
   ```python
   if result.confidence > 0.8:
       print("High confidence result")
   ```

## Common Issues

### Issue 1: LLM not available
```python
# Check Ollama is running
# curl http://localhost:11434/api/tags

# Or configure different provider
config = AgentConfig(
    llm_provider="openai",
    llm_model="gpt-3.5-turbo"
)
```

### Issue 2: Memory issues
```python
# Reset agent memory
agent.reset()

# Or disable memory
config = AgentConfig(enable_memory=False)
```

### Issue 3: Timeout
```python
# Increase timeout
config = AgentConfig(timeout=600)  # 10 minutes
```

## Resources

- Full Documentation: `docs/MULTI_AGENT_SYSTEM.md`
- Examples: `examples/multi_agent_examples.py`
- Tests: `tests/test_agents_quick.py`
- Summary: `AGENT_SYSTEM_SUMMARY.md`

## File Locations

```
omnisense/agents/
├── __init__.py          # Package exports
├── base.py              # Base agent class
├── manager.py           # Agent manager
├── scout.py             # Scout agent
├── analyst.py           # Analyst agent
├── ecommerce.py         # Ecommerce agent
├── academic.py          # Academic agent
├── creator.py           # Creator agent
└── report.py            # Report agent
```

---

**Quick Start**: Import → Create → Process → Get Results

**That's it!** You're ready to use the OmniSense multi-agent system. 🚀
