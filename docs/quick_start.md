# OmniSense Quick Start Guide

Get started with OmniSense in minutes! This guide will help you install, configure, and run your first data collection and analysis.

## Table of Contents

- [Installation](#installation)
- [Quick Examples](#quick-examples)
- [Common Use Cases](#common-use-cases)
- [Next Steps](#next-steps)

## Installation

### Option 1: Docker Installation (Recommended)

Docker provides the easiest way to get started with OmniSense.

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+

**Steps:**

```bash
# Clone the repository
git clone https://github.com/bingdongni/omnisense.git
cd omnisense

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f omnisense
```

**Access the interfaces:**
- Web UI: http://localhost:8501
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (admin/minioadmin)

**Stop services:**
```bash
docker-compose down
```

### Option 2: Local Installation

For development or customization, install OmniSense locally.

**Prerequisites:**
- Python 3.11 or higher
- pip package manager
- Git

**Steps:**

```bash
# Clone the repository
git clone https://github.com/bingdongni/omnisense.git
cd omnisense

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create necessary directories
mkdir -p data logs cache

# Copy environment template
cp .env.example .env  # Edit with your settings

# Start the Web UI
streamlit run app.py

# Or start the API server
python api.py

# Or use the CLI
python cli.py --help
```

### Option 3: pip Installation (Coming Soon)

```bash
pip install omnisense
```

## Quick Examples

### Example 1: First Data Collection

Collect videos from Douyin (TikTok China) about "AI Programming":

**Using Python:**

```python
from omnisense import OmniSense

# Initialize OmniSense
omni = OmniSense()

# Collect data from Douyin
result = omni.collect(
    platform="douyin",
    keyword="AI编程",
    max_count=50
)

print(f"Collected {result['count']} items")
print(f"First item: {result['data'][0]['title']}")
```

**Using CLI:**

```bash
python cli.py collect \
    --platform douyin \
    --keyword "AI编程" \
    --max-count 50 \
    --output data/douyin_results.json
```

**Using API:**

```bash
# First, get authentication token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Start collection task
curl -X POST "http://localhost:8000/api/v1/collect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "douyin",
    "keyword": "AI编程",
    "max_count": 50
  }'

# Check task status
curl "http://localhost:8000/api/v1/collect/TASK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example 2: Analyze Collected Data

Perform sentiment analysis and clustering on collected data:

**Using Python:**

```python
from omnisense import OmniSense

omni = OmniSense()

# Collect data
result = omni.collect(
    platform="xiaohongshu",
    keyword="护肤品推荐",
    max_count=100
)

# Analyze with AI agents
analysis = omni.analyze(
    data=result,
    agents=["analyst", "creator"],
    analysis_types=["sentiment", "clustering"]
)

print("Sentiment Analysis:")
print(analysis['analysis']['sentiment'])

print("\nTop Clusters:")
for cluster in analysis['analysis']['clustering']['clusters']:
    print(f"- {cluster['label']}: {cluster['count']} items")
```

**Using CLI:**

```bash
# Collect data
python cli.py collect \
    --platform xiaohongshu \
    --keyword "护肤品推荐" \
    --output data/xiaohongshu.json

# Analyze data
python cli.py analyze \
    --input data/xiaohongshu.json \
    --agents analyst creator \
    --analysis sentiment clustering \
    --output data/analysis.json
```

### Example 3: Generate Report

Create a professional PDF report from analysis results:

**Using Python:**

```python
from omnisense import OmniSense

omni = OmniSense()

# Collect and analyze
result = omni.collect(platform="weibo", keyword="电动汽车", max_count=200)
analysis = omni.analyze(data=result, agents=["analyst"])

# Generate PDF report
report_path = omni.generate_report(
    analysis=analysis,
    format="pdf",
    output="reports/weibo_ev_analysis.pdf"
)

print(f"Report saved to: {report_path}")
```

**Using CLI:**

```bash
python cli.py report \
    --input data/analysis.json \
    --format pdf \
    --output reports/analysis_report.pdf
```

## Common Use Cases

### Use Case 1: Content Creator - Find Trending Topics

Identify trending topics across multiple platforms:

```python
from omnisense import OmniSense

omni = OmniSense()

platforms = ["douyin", "xiaohongshu", "weibo"]
results = {}

# Collect from multiple platforms
for platform in platforms:
    results[platform] = omni.collect(
        platform=platform,
        keyword="美食",
        max_count=100
    )

# Analyze trends
analysis = omni.analyze(
    data=results,
    agents=["scout", "creator"],
    analysis_types=["trend"]
)

# Get top trending topics
for topic in analysis['agents']['scout']['trends']:
    print(f"Trending: {topic['trend']} ({topic['type']})")
```

### Use Case 2: E-commerce - Product Research

Research products and analyze reviews:

```python
from omnisense import OmniSense

omni = OmniSense()

# Search for product reviews on Amazon
result = omni.collect(
    platform="amazon",
    keyword="wireless earbuds",
    max_count=200,
    filters={
        "min_rating": 4.0,
        "verified_purchase": True
    }
)

# Analyze with E-commerce agent
analysis = omni.analyze(
    data=result,
    agents=["ecommerce"],
    analysis_types=["sentiment", "clustering"]
)

# Get insights
print("Average Rating:", analysis['agents']['ecommerce']['avg_rating'])
print("Top Features:", analysis['agents']['ecommerce']['top_features'])
print("Common Complaints:", analysis['agents']['ecommerce']['complaints'])
```

### Use Case 3: Academic Research

Search and analyze academic papers:

```python
from omnisense import OmniSense

omni = OmniSense()

# Search Google Scholar
result = omni.collect(
    platform="google_scholar",
    keyword="machine learning interpretability",
    max_count=50,
    filters={
        "year_from": 2020,
        "sort": "relevance"
    }
)

# Analyze with Academic agent
analysis = omni.analyze(
    data=result,
    agents=["academic"],
    analysis_types=["clustering"]
)

# Generate literature review
report = omni.generate_report(
    analysis=analysis,
    format="docx",
    template="academic",
    output="literature_review.docx"
)
```

### Use Case 4: Brand Monitoring

Monitor brand mentions across social media:

```python
from omnisense import OmniSense
import schedule
import time

omni = OmniSense()

def monitor_brand():
    """Monitor brand mentions"""
    platforms = ["weibo", "xiaohongshu", "zhihu"]
    brand = "特斯拉"

    all_data = []

    for platform in platforms:
        result = omni.collect(
            platform=platform,
            keyword=brand,
            max_count=100
        )
        all_data.extend(result['data'])

    # Analyze sentiment
    analysis = omni.analyze(
        data=all_data,
        agents=["analyst"],
        analysis_types=["sentiment"]
    )

    # Alert on negative sentiment
    sentiment_score = analysis['analysis']['sentiment']['average_score']
    if sentiment_score < 0.4:
        print(f"ALERT: Negative sentiment detected! Score: {sentiment_score}")
        # Send notification (email, Slack, etc.)

    # Generate daily report
    omni.generate_report(
        analysis=analysis,
        format="html",
        output=f"reports/brand_monitor_{time.strftime('%Y%m%d')}.html"
    )

# Run every 6 hours
schedule.every(6).hours.do(monitor_brand)

# Run immediately once
monitor_brand()

# Keep running
while True:
    schedule.run_pending()
    time.sleep(3600)
```

### Use Case 5: Competitive Analysis

Compare competitors across platforms:

```python
from omnisense import OmniSense

omni = OmniSense()

competitors = ["Brand_A", "Brand_B", "Brand_C"]
results = {}

# Collect data for each competitor
for competitor in competitors:
    results[competitor] = omni.collect(
        platform="xiaohongshu",
        keyword=competitor,
        max_count=100
    )

# Comparative analysis
analysis = omni.analyze(
    data=results,
    agents=["analyst"],
    analysis_types=["comparison", "sentiment"]
)

# Generate comparison report
report = omni.generate_report(
    analysis=analysis,
    format="pdf",
    template="comparison",
    output="competitive_analysis.pdf"
)

print("Comparison Results:")
for comp in analysis['analysis']['comparison']:
    print(f"{comp['name']}: Sentiment {comp['sentiment']}, Engagement {comp['engagement']}")
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Debug mode
DEBUG=false
LOG_LEVEL=INFO

# Database
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Proxy (optional)
PROXY_ENABLED=false
HTTP_PROXY=
HTTPS_PROXY=

# Anti-Crawl
USER_AGENT_ROTATION=true
FINGERPRINT_RANDOM=true
REQUEST_DELAY_MIN=1.0
REQUEST_DELAY_MAX=5.0

# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# API Keys (if using cloud LLMs)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Captcha Service (optional)
CAPTCHA_SERVICE=
CAPTCHA_API_KEY=
```

### Advanced Configuration

For advanced configuration, create a `config.yaml`:

```yaml
# Anti-crawl settings
anti_crawl:
  user_agent_rotation: true
  fingerprint_random: true
  request_delay_min: 1.0
  request_delay_max: 5.0
  max_retries: 3

# Spider settings
spider:
  concurrent_tasks: 5
  timeout: 30
  download_media: true
  cookie_persist: true

# Agent settings
agent:
  llm_provider: ollama
  llm_model: qwen2.5:7b
  llm_temperature: 0.7
  llm_max_tokens: 4096

# Platform settings
platform:
  enabled_platforms:
    - douyin
    - xiaohongshu
    - weibo
    - bilibili
    - amazon
```

Load custom configuration:

```python
from omnisense import OmniSense

omni = OmniSense(config_file="config.yaml")
```

## Troubleshooting

### Common Issues

**Issue: Playwright browser not installed**
```bash
playwright install chromium
```

**Issue: Redis connection failed**
- Ensure Redis is running: `docker run -d -p 6379:6379 redis:7-alpine`
- Check Redis connection: `redis-cli ping`

**Issue: Rate limited by platform**
- Increase delay in config: `request_delay_min: 3.0, request_delay_max: 8.0`
- Enable proxy pool
- Reduce concurrent tasks

**Issue: Captcha blocking collection**
- Configure captcha service in .env
- Reduce collection speed
- Use cookie-based authentication

**Issue: Memory usage high**
- Reduce `max_count` per collection
- Enable media download filtering
- Use pagination for large datasets

## Next Steps

1. **Explore Platform Guides**: Learn platform-specific features in [docs/platforms/](./platforms/)
2. **Read API Documentation**: Full API reference at [docs/api.md](./api.md)
3. **Developer Guide**: Extend OmniSense with custom platforms at [docs/developer_guide.md](./developer_guide.md)
4. **Check FAQ**: Common questions answered at [docs/faq.md](./faq.md)

## Getting Help

- **GitHub Issues**: https://github.com/bingdongni/omnisense/issues
- **Discussions**: https://github.com/bingdongni/omnisense/discussions
- **Email**: bingdongni@example.com

## What's Next?

Now that you've completed the quick start:

1. Try collecting data from different platforms
2. Experiment with different AI agents
3. Create custom analysis pipelines
4. Integrate OmniSense into your applications

Happy data exploring!
