"""
Example: Basic data collection and analysis

This example shows how to:
1. Collect data from a platform
2. Analyze the collected data
3. Visualize results
4. Generate a report
"""

import asyncio
from omnisense import OmniSense


async def main():
    # Initialize OmniSense
    omni = OmniSense()

    # Example 1: Collect Douyin videos
    print("=" * 50)
    print("Example 1: Collecting Douyin Videos")
    print("=" * 50)

    result = omni.collect(
        platform="douyin",
        keyword="人工智能",
        max_count=50
    )

    print(f"✓ Collected {result['count']} videos")
    print(f"Platform: {result['platform']}")

    # Example 2: Analyze sentiment
    print("\n" + "=" * 50)
    print("Example 2: Sentiment Analysis")
    print("=" * 50)

    analysis = omni.analyze(
        data=result,
        analysis_types=["sentiment", "clustering"]
    )

    if 'sentiment' in analysis.get('analysis', {}):
        sentiment = analysis['analysis']['sentiment']
        print(f"✓ Average sentiment score: {sentiment.get('average_score', 0):.2f}")
        print(f"Positive ratio: {sentiment.get('positive_ratio', 0):.2%}")
        print(f"Negative ratio: {sentiment.get('negative_ratio', 0):.2%}")

    # Example 3: Visualize results
    print("\n" + "=" * 50)
    print("Example 3: Visualization")
    print("=" * 50)

    charts = omni.visualize(
        data=analysis,
        chart_types=["bar", "wordcloud"]
    )

    print(f"✓ Generated {len(charts)} charts")

    # Example 4: Generate report
    print("\n" + "=" * 50)
    print("Example 4: Report Generation")
    print("=" * 50)

    report_path = omni.generate_report(
        analysis=analysis,
        format="html",
        output="examples/output/report.html"
    )

    print(f"✓ Report saved to: {report_path}")

    # Clean up
    await omni.close()
    print("\n" + "=" * 50)
    print("✓ Example completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
