#!/usr/bin/env python
"""
OmniSense CLI Tool
Command-line interface for data collection and analysis
"""

import click
import asyncio
import json
from pathlib import Path
from typing import Optional

from omnisense import OmniSense
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    🎯 OmniSense - Cross-Platform Data Intelligence System

    聚析：全域数据智能洞察平台
    """
    pass


@cli.command()
@click.option('--platform', '-p', required=True, help='Platform name (douyin, xiaohongshu, etc.)')
@click.option('--keyword', '-k', help='Search keyword')
@click.option('--user-id', '-u', help='User ID to scrape')
@click.option('--url', help='Direct URL to scrape')
@click.option('--max-count', '-n', default=100, help='Maximum items to collect')
@click.option('--output', '-o', default='data/output.json', help='Output file path')
def collect(platform: str, keyword: Optional[str], user_id: Optional[str],
           url: Optional[str], max_count: int, output: str):
    """Collect data from platform"""

    click.echo(f"🚀 Starting data collection from {platform}...")

    omni = OmniSense()

    try:
        result = omni.collect(
            platform=platform,
            keyword=keyword,
            user_id=user_id,
            url=url,
            max_count=max_count
        )

        # Save results
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        click.echo(f"✅ Collected {result['count']} items")
        click.echo(f"📁 Saved to {output}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--input', '-i', required=True, help='Input data file')
@click.option('--agents', '-a', multiple=True, help='Agents to use (analyst, creator, etc.)')
@click.option('--analysis', '-t', multiple=True, help='Analysis types (sentiment, clustering, etc.)')
@click.option('--output', '-o', default='data/analysis.json', help='Output file path')
def analyze(input: str, agents: tuple, analysis: tuple, output: str):
    """Analyze collected data"""

    click.echo(f"📊 Starting analysis...")

    # Load input data
    with open(input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    omni = OmniSense()

    try:
        result = omni.analyze(
            data=data,
            agents=list(agents) if agents else None,
            analysis_types=list(analysis) if analysis else None
        )

        # Save results
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        click.echo(f"✅ Analysis complete")
        click.echo(f"📁 Saved to {output}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--input', '-i', required=True, help='Analysis results file')
@click.option('--format', '-f', default='pdf', help='Report format (pdf, docx, html)')
@click.option('--output', '-o', default='report.pdf', help='Output file path')
@click.option('--template', '-t', help='Report template')
def report(input: str, format: str, output: str, template: Optional[str]):
    """Generate report from analysis"""

    click.echo(f"📄 Generating {format.upper()} report...")

    # Load analysis data
    with open(input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    omni = OmniSense()

    try:
        report_path = omni.generate_report(
            analysis=data,
            format=format,
            output=output,
            template=template
        )

        click.echo(f"✅ Report generated")
        click.echo(f"📁 Saved to {report_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
def platforms():
    """List supported platforms"""

    omni = OmniSense()
    platforms = omni.get_supported_platforms()

    click.echo("\n🌐 Supported Platforms:\n")

    # Group by category
    categories = {
        'Short Video': ['douyin', 'kuaishou', 'tiktok', 'youtube', 'bilibili'],
        'Social Media': ['weibo', 'xiaohongshu', 'twitter', 'instagram', 'facebook'],
        'E-commerce': ['amazon', 'taobao', 'tmall', 'jd', 'pinduoduo'],
        'Academic': ['google_scholar', 'cnki', 'arxiv'],
        'Developer': ['github', 'csdn', 'stackoverflow']
    }

    for category, platform_list in categories.items():
        available = [p for p in platform_list if p in platforms]
        if available:
            click.echo(f"  {category}:")
            for platform in available:
                click.echo(f"    ✓ {platform}")
            click.echo()

    click.echo(f"Total: {len(platforms)} platforms\n")


@cli.command()
@click.option('--host', default='localhost', help='Host to bind')
@click.option('--port', default=8501, help='Port to bind')
def web(host: str, port: int):
    """Launch web interface"""

    click.echo(f"🌐 Starting web interface at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")

    import subprocess
    subprocess.run([
        'streamlit', 'run', 'app.py',
        '--server.address', host,
        '--server.port', str(port)
    ])


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind')
@click.option('--port', default=8000, help='Port to bind')
def api(host: str, port: int):
    """Launch API server"""

    click.echo(f"🚀 Starting API server at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")

    import subprocess
    subprocess.run([
        'uvicorn', 'api:app',
        '--host', host,
        '--port', str(port),
        '--reload'
    ])


@cli.command()
def version():
    """Show version information"""

    click.echo("\n┌─────────────────────────────────────┐")
    click.echo("│   OmniSense / 聚析                  │")
    click.echo("│   v1.0.0                            │")
    click.echo("│   Cross-Platform Data Intelligence  │")
    click.echo("└─────────────────────────────────────┘\n")
    click.echo("Author: bingdongni")
    click.echo("License: MIT")
    click.echo("GitHub: https://github.com/bingdongni/omnisense\n")


if __name__ == '__main__':
    cli()
