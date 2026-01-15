"""
Example: OmniSense Multi-Agent System Usage
演示多智能体系统的使用方法
"""

import asyncio
from omnisense.agents import (
    AgentManager,
    ScoutAgent,
    AnalystAgent,
    EcommerceAgent,
    AcademicAgent,
    CreatorAgent,
    ReportAgent,
    AgentConfig,
    AgentRole
)


async def example_1_basic_agent_usage():
    """Example 1: Basic agent usage"""
    print("=== Example 1: Basic Agent Usage ===\n")

    # Create scout agent
    scout = ScoutAgent()

    # Process discovery task
    task = {
        "type": "discover",
        "data": [
            {"title": "Product A", "views": 1000},
            {"title": "Product B", "views": 2000},
            {"title": "Product C", "views": 1500}
        ],
        "platform": "douyin"
    }

    result = await scout.process(task)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Discoveries: {len(result.data.get('discoveries', []))}")
    print(f"Confidence: {result.confidence}\n")


async def example_2_agent_collaboration():
    """Example 2: Agent collaboration"""
    print("=== Example 2: Agent Collaboration ===\n")

    # Create agents
    scout = ScoutAgent()
    analyst = AnalystAgent()

    # Collaborate on a task
    task = {
        "type": "discover",
        "data": [{"content": "AI technology trends"}],
        "platform": "zhihu"
    }

    result = await scout.collaborate(analyst, task)
    print(f"Collaboration success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Agents involved: {result.metadata.get('agents', [])}\n")


async def example_3_agent_manager():
    """Example 3: Agent Manager orchestration"""
    print("=== Example 3: Agent Manager Orchestration ===\n")

    # Initialize manager
    manager = AgentManager()

    # Register agents
    manager.register_agent(ScoutAgent())
    manager.register_agent(AnalystAgent())
    manager.register_agent(EcommerceAgent())

    # Submit tasks
    task_ids = []

    # Task 1: Scout discovers content
    task_id_1 = await manager.submit_task(
        agent_role=AgentRole.SCOUT,
        parameters={
            "type": "discover",
            "data": [{"title": "Product A"}],
            "platform": "taobao"
        },
        priority="high"
    )
    task_ids.append(task_id_1)

    # Task 2: Analyst analyzes (depends on Task 1)
    task_id_2 = await manager.submit_task(
        agent_role=AgentRole.ANALYST,
        parameters={
            "type": "deep_analysis",
            "data": [{"price": 100, "rating": 4.5}],
            "analysis_type": "product"
        },
        dependencies=[task_id_1]
    )
    task_ids.append(task_id_2)

    # Task 3: Ecommerce provides recommendations
    task_id_3 = await manager.submit_task(
        agent_role=AgentRole.ECOMMERCE,
        parameters={
            "type": "purchase_recommendation",
            "products": [
                {"name": "Product A", "price": 100, "rating": 4.5},
                {"name": "Product B", "price": 150, "rating": 4.8}
            ],
            "budget": 200
        },
        priority="medium"
    )
    task_ids.append(task_id_3)

    # Run all tasks
    results = await manager.run_all_tasks(max_concurrent=2)

    print(f"Total tasks completed: {len(results)}")
    for i, result in enumerate(results):
        print(f"Task {i+1}: {result.message}")

    # Get metrics
    metrics = manager.get_metrics()
    print(f"\nMetrics:")
    print(f"- Total tasks: {metrics['tasks']['total']}")
    print(f"- Completed: {metrics['tasks']['completed']}")
    print(f"- Failed: {metrics['tasks']['failed']}\n")


async def example_4_ecommerce_workflow():
    """Example 4: E-commerce analysis workflow"""
    print("=== Example 4: E-commerce Analysis Workflow ===\n")

    manager = AgentManager()
    manager.register_agent(ScoutAgent())
    manager.register_agent(EcommerceAgent())
    manager.register_agent(ReportAgent())

    # Define workflow
    workflow = [
        {
            "role": AgentRole.SCOUT,
            "parameters": {
                "type": "discover",
                "data": [
                    {"name": "Smartphone A", "price": 999, "rating": 4.5},
                    {"name": "Smartphone B", "price": 1299, "rating": 4.8},
                    {"name": "Smartphone C", "price": 799, "rating": 4.2}
                ],
                "platform": "amazon"
            },
            "depends_on": []
        },
        {
            "role": AgentRole.ECOMMERCE,
            "parameters": {
                "type": "competitive_analysis",
                "target_product": {"name": "Smartphone A", "price": 999},
                "competitors": [
                    {"name": "Smartphone B", "price": 1299},
                    {"name": "Smartphone C", "price": 799}
                ]
            },
            "depends_on": [0]
        },
        {
            "role": AgentRole.REPORT,
            "parameters": {
                "type": "generate_report",
                "topic": "Smartphone Market Analysis",
                "data": {},
                "analysis": {},
                "audience": "product_manager"
            },
            "depends_on": [0, 1]
        }
    ]

    # Execute workflow
    results = await manager.orchestrate_workflow(workflow)

    print(f"Workflow completed with {len(results)} steps")
    for step_idx, result in results.items():
        print(f"Step {step_idx}: {result.agent_name} - {result.message}\n")


async def example_5_academic_research():
    """Example 5: Academic research workflow"""
    print("=== Example 5: Academic Research Workflow ===\n")

    academic = AcademicAgent()

    # Analyze a research paper
    paper_task = {
        "type": "paper_analysis",
        "title": "Deep Learning for Natural Language Processing",
        "authors": ["Author A", "Author B"],
        "abstract": "This paper presents a comprehensive study of deep learning techniques...",
        "content": "Introduction: Deep learning has revolutionized NLP..."
    }

    result = await academic.process(paper_task)
    print(f"Paper analysis: {result.message}")
    print(f"Quality score: {result.data.get('quality_score', 0)}/100")

    # Identify research trends
    trend_task = {
        "type": "trend_analysis",
        "research_area": "Natural Language Processing",
        "papers": [
            {"title": "BERT: Pre-training of Deep Bidirectional Transformers", "year": 2018},
            {"title": "GPT-3: Language Models are Few-Shot Learners", "year": 2020},
            {"title": "ChatGPT and LLMs", "year": 2023}
        ],
        "timeframe": "2018-2023"
    }

    trend_result = await academic.process(trend_task)
    print(f"\nTrend analysis: {trend_result.message}")
    print(f"Trends found: {trend_result.data.get('trends', [])}\n")


async def example_6_content_creation():
    """Example 6: Content creation workflow"""
    print("=== Example 6: Content Creation Workflow ===\n")

    creator = CreatorAgent()

    # Generate content
    gen_task = {
        "type": "generate_content",
        "topic": "Sustainable Living Tips",
        "platform": "xiaohongshu",
        "audience": "millennials",
        "tone": "friendly",
        "constraints": {"max_length": 500}
    }

    result = await creator.process(gen_task)
    print(f"Content generated: {result.message}")
    print(f"Engagement prediction: {result.data.get('engagement_prediction', 0)}/100")
    print(f"Content preview: {result.data.get('content', '')[:100]}...")

    # Suggest hashtags
    hashtag_task = {
        "type": "suggest_hashtags",
        "content": result.data.get('content', ''),
        "platform": "xiaohongshu",
        "niche": "lifestyle",
        "reach_type": "balanced"
    }

    hashtag_result = await creator.process(hashtag_task)
    print(f"\nHashtags suggested: {hashtag_result.data.get('total_count', 0)}")
    print(f"Sample hashtags: {hashtag_result.data.get('hashtags', [])[:5]}\n")


async def example_7_complete_analysis_pipeline():
    """Example 7: Complete analysis pipeline"""
    print("=== Example 7: Complete Analysis Pipeline ===\n")

    manager = AgentManager()

    # Register all agents
    manager.register_agent(ScoutAgent())
    manager.register_agent(AnalystAgent())
    manager.register_agent(EcommerceAgent())
    manager.register_agent(CreatorAgent())
    manager.register_agent(ReportAgent())

    # Multi-agent collaboration
    agents = [
        manager.get_agent_by_role(AgentRole.SCOUT),
        manager.get_agent_by_role(AgentRole.ANALYST),
        manager.get_agent_by_role(AgentRole.ECOMMERCE)
    ]

    task = {
        "type": "product_analysis",
        "product_name": "Wireless Headphones",
        "platform": "amazon",
        "details": {"price": 199, "rating": 4.6},
        "reviews": ["Great sound", "Battery life is amazing", "Comfortable"]
    }

    result = await manager.collaborate_agents(agents, task)
    print(f"Collaboration result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Confidence: {result.confidence}")
    print(f"Agents: {result.metadata.get('agents', [])}\n")


async def example_8_report_generation():
    """Example 8: Report generation"""
    print("=== Example 8: Report Generation ===\n")

    report = ReportAgent()

    # Generate comprehensive report
    report_task = {
        "type": "generate_report",
        "topic": "Social Media Marketing Analysis Q1 2024",
        "data": {
            "platforms": ["douyin", "xiaohongshu", "weibo"],
            "metrics": {"engagement": 15000, "reach": 50000}
        },
        "analysis": {
            "top_content": "Video content",
            "best_time": "7pm-9pm"
        },
        "audience": "marketing_team",
        "template": "executive"
    }

    result = await report.process(report_task)
    print(f"Report generated: {result.message}")
    print(f"Sections: {result.data.get('section_count', 0)}")

    # Format as markdown
    format_task = {
        "type": "format_report",
        "report_data": result.data.get('report', {}),
        "format": "markdown"
    }

    format_result = await report.process(format_task)
    print(f"\nFormatted report size: {format_result.data.get('size', 0)} characters")
    print(f"Format: {format_result.data.get('format', 'N/A')}\n")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("OmniSense Multi-Agent System Examples")
    print("=" * 60 + "\n")

    # Run examples
    await example_1_basic_agent_usage()
    await example_2_agent_collaboration()
    await example_3_agent_manager()
    await example_4_ecommerce_workflow()
    await example_5_academic_research()
    await example_6_content_creation()
    await example_7_complete_analysis_pipeline()
    await example_8_report_generation()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
