# OmniSense

<div align="center">

![OmniSense Logo](images/logo.png)

**Cross-Platform Data Intelligence & Insight System**

[![GitHub Stars](https://img.shields.io/github/stars/bingdongni/omnisense?style=social)](https://github.com/bingdongni/omnisense)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-supported-brightgreen)](Dockerfile)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[中文文档](../README.md) | English

</div>

## Overview

OmniSense is a powerful **Cross-Platform Data Intelligence & Insight System** that provides independent, customized full-stack mechanisms for 49 mainstream platforms covering data collection, anti-bot evasion, content matching, and interaction processing. Through a multi-agent collaboration system, it enables end-to-end automation from data collection to intelligent analysis.

### Key Features

- **49 Platform-Specific Mechanisms** - Independent customized crawling, anti-bot, matching, and interaction processing for each platform
- **Multi-Agent Collaboration** - Six intelligent agents: Scout, Analyst, Ecommerce, Academic, Creator, and Report
- **Robust Anti-Bot System** - Smart IP pools, fingerprint spoofing, CAPTCHA handling, behavioral simulation
- **Precision Content Matching** - BERT-based semantic analysis + SimHash deduplication + FAISS vector search
- **Interaction Data Processing** - Comment thread collection, sentiment analysis, hotspot extraction, relationship graphs
- **Data Visualization** - ECharts charts + word clouds + network graphs + multi-dimensional data display
- **Zero-Barrier Deployment** - Docker one-click deployment + Web UI + Desktop GUI + CLI tools
- **Highly Extensible** - Modular design supporting rapid addition of new platforms and features

### Supported Platform Matrix

| Category | Platforms (49 Total) |
|----------|----------------------|
| **Short Video** | Douyin, Kuaishou, TikTok, YouTube, Bilibili |
| **Social Media** | Weibo, Xiaohongshu (RedNote), Maimai, Twitter (X), Facebook, Instagram, LinkedIn, Reddit |
| **Content Communities** | WeChat Official Accounts, WeChat Channels, Zhihu, Douban, Hupu, Baidu Tieba, Toutiao, Sohu, Autohome/Dongchedi, Xueqiu, Quora, Medium |
| **Cross-Border E-commerce** | Amazon, Temu, Shopee, Ozon, Taobao, Tmall, JD.com, Pinduoduo, Xianyu, Dewu, Vipshop |
| **Local Services** | Meituan, Dianping |
| **Recommerce** | Zhuanzhuan, Aihuishou |
| **Search Engines** | Baidu, Google, Quark |
| **Academic Platforms** | Google Scholar, CNKI, Web of Science, arXiv |
| **Developer Communities** | GitHub, CSDN, Stack Overflow |

## Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/bingdongni/omnisense.git
cd omnisense

# Start services
docker-compose up -d

# Access Web UI
open http://localhost:8501
```

### Option 2: Local Installation

```bash
# Clone repository
git clone https://github.com/bingdongni/omnisense.git
cd omnisense

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Start Web UI
streamlit run app.py

# Or use CLI
python cli.py --help
```

### Quick Example

```python
from omnisense import OmniSense

# Initialize
omni = OmniSense()

# Collect and analyze Douyin videos
result = omni.collect(
    platform="douyin",
    keyword="AI Programming",
    max_count=100
)

# Intelligent analysis
analysis = omni.analyze(
    data=result,
    agents=["analyst", "creator"]
)

# Generate report
omni.generate_report(
    analysis=analysis,
    format="pdf",
    output="report.pdf"
)
```

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface Layer                  │
│              Streamlit Web + PyQt5 GUI + CLI             │
├─────────────────────────────────────────────────────────┤
│                    Report Generation Layer               │
│           Jinja2 Templates + WeasyPrint PDF + Word       │
├─────────────────────────────────────────────────────────┤
│                    Visualization Layer                   │
│              ECharts + Plotly + WordCloud + NetworkX     │
├─────────────────────────────────────────────────────────┤
│                    Intelligent Analysis Layer            │
│           Multi-Agent System (LangChain + Ollama)        │
├─────────────────────────────────────────────────────────┤
│                    Interaction Processing Layer          │
│           49 Platform-Specific Engines + Sentiment       │
├─────────────────────────────────────────────────────────┤
│                    Smart Matching Layer                  │
│           49 Platform Matchers + BERT Semantics          │
├─────────────────────────────────────────────────────────┤
│                    Data Storage Layer                    │
│           SQLite + ChromaDB + Redis + MinIO              │
├─────────────────────────────────────────────────────────┤
│                    Data Collection Layer                 │
│           49 Platform-Specific Spiders + Playwright      │
├─────────────────────────────────────────────────────────┤
│                    Anti-Bot Layer                        │
│           IP Pool + Fingerprint + CAPTCHA Handler        │
└─────────────────────────────────────────────────────────┘
```

## Core Capabilities

### 1. Data Collection

- 49 platform-specific collection mechanisms
- Multi-threaded/asynchronous concurrent collection
- Smart deduplication and incremental updates
- Automatic media file downloads
- Real-time progress monitoring

### 2. Anti-Bot System

- Smart IP pool rotation
- Browser fingerprint spoofing
- Automatic CAPTCHA handling
- Human behavior simulation
- Cookie pool management

### 3. Content Matching

- Multi-modal semantic understanding
- Similarity-based deduplication
- Vector similarity search
- Popularity-weighted ranking
- Smart tag classification

### 4. Interaction Analysis

- Deep comment thread collection
- Sentiment tendency analysis
- Hot keyword extraction
- User profile construction
- Propagation path tracking

### 5. Intelligent Agents

| Agent | Capabilities |
|-------|-------------|
| Scout | Cross-platform data exploration, trend discovery, trend tracking |
| Analyst | Sentiment analysis, topic clustering, competitive comparison |
| Ecommerce | Product selection analysis, price monitoring, review analysis |
| Academic | Literature retrieval, citation analysis, knowledge graphs |
| Creator | Viral content analysis, topic recommendations, title optimization |
| Report | Multi-template, multi-format report generation |

### 6. Data Visualization

- Interactive charts (line, bar, pie charts)
- Word clouds
- Social network graphs
- Geographic heat maps
- Time series analysis

## Use Cases

### Content Creators

- Viral content analysis
- Topic trend tracking
- Competitive monitoring
- Fan engagement insights

### Cross-Border E-commerce

- Product selection data analysis
- Competitive price monitoring
- Review sentiment analysis
- Market trend forecasting

### Academic Research

- Batch literature retrieval
- Citation relationship analysis
- Research trend tracking
- Automated review generation

### Market Research

- Cross-platform public opinion monitoring
- Brand voice analysis
- Consumer insights
- Industry trend reports

### Developers

- Technology trend analysis
- Open source project monitoring
- Community activity tracking
- Technology stack selection

## Documentation

- [Quick Start](quick_start.md)
- [Platform Usage Guides](platforms/)
- [Developer Guide](developer_guide.md)
- [API Documentation](api.md)
- [FAQ](faq.md)
- [Contributing Guide](../CONTRIBUTING.md)

## Technology Stack

| Category | Technologies |
|----------|-------------|
| Core Language | Python 3.11+ |
| Web Frameworks | Streamlit, FastAPI |
| Crawling | Playwright, aiohttp, Requests |
| Anti-Bot | ProxyPool, FingerprintSwitcher |
| NLP | BERT, sentence-transformers |
| Agents | LangChain, Ollama |
| Databases | SQLite, ChromaDB, Redis |
| Storage | MinIO |
| Visualization | ECharts, Plotly, WordCloud |
| Deployment | Docker, Docker Compose |

## API Quick Reference

### Authentication

```bash
# Get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

### Data Collection

```bash
# Start collection task
curl -X POST "http://localhost:8000/api/v1/collect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "douyin",
    "keyword": "AI programming",
    "max_count": 100
  }'

# Check task status
curl "http://localhost:8000/api/v1/collect/{task_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Data Analysis

```bash
# Start analysis task
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [...],
    "agents": ["analyst"],
    "analysis_types": ["sentiment", "clustering"]
  }'
```

### Platform Information

```bash
# List all platforms
curl "http://localhost:8000/api/v1/platforms" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Full API documentation: [docs/api.md](api.md)

## CLI Commands

```bash
# Collect data
python cli.py collect --platform douyin --keyword "AI" --max-count 100

# Analyze data
python cli.py analyze --input data.json --agents analyst creator

# Generate report
python cli.py report --input analysis.json --format pdf --output report.pdf

# List platforms
python cli.py platforms

# Launch web interface
python cli.py web

# Launch API server
python cli.py api
```

## Contributing

We welcome all forms of contributions! Please check the [Contributing Guide](../CONTRIBUTING.md) for details.

### Contributor Incentives

- Core contributor attribution and showcase
- Free Pro version subscription (worth $499/year)
- Technical exposure opportunities
- Custom merchandise

### Current Contributors

<a href="https://github.com/bingdongni/omnisense/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bingdongni/omnisense" />
</a>

## Roadmap

### Version 1.1 (Q2 2024)

- [ ] Add 20+ more platforms
- [ ] Real-time data streaming
- [ ] Advanced ML models integration
- [ ] Mobile app (iOS/Android)

### Version 1.2 (Q3 2024)

- [ ] Custom agent builder
- [ ] Distributed crawling support
- [ ] Advanced NLP pipelines
- [ ] Enterprise features

### Version 2.0 (Q4 2024)

- [ ] Multi-language support
- [ ] Cloud-native architecture
- [ ] Advanced AI analytics
- [ ] Enterprise SaaS platform

## Performance

- **Collection Speed**: Up to 10,000 items/hour per platform
- **Analysis Speed**: 1,000 items analyzed in < 5 minutes
- **Concurrency**: Supports 100+ concurrent tasks
- **Scalability**: Horizontal scaling with distributed architecture
- **Reliability**: 99.9% uptime with proper infrastructure

## Security & Privacy

- Only collects publicly available data
- No private information collection
- Complies with platform Terms of Service
- Respects robots.txt
- User data encryption
- Secure credential storage

## License

This project is licensed under the [MIT License](../LICENSE).

## Disclaimer

1. This project is for educational and research purposes only
2. Only collects publicly available data, no private information
3. Users must comply with target platform Terms of Service and robots.txt
4. Users bear all legal responsibilities for using this project

## Contact

- **GitHub Issues**: [Submit Issues](https://github.com/bingdongni/omnisense/issues)
- **GitHub Discussions**: [Join Discussions](https://github.com/bingdongni/omnisense/discussions)
- **Email**: bingdongni@example.com
- **WeChat**: omnisense_official (Scan QR code in docs)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=bingdongni/omnisense&type=Date)](https://star-history.com/#bingdongni/omnisense&Date)

## Acknowledgments

Special thanks to all contributors and the following open-source projects:

- [Playwright](https://playwright.dev/) - Browser automation
- [LangChain](https://www.langchain.com/) - Agent framework
- [Streamlit](https://streamlit.io/) - Web interface
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [Ollama](https://ollama.ai/) - Local LLM runtime

## Citation

If you use OmniSense in your research, please cite:

```bibtex
@software{omnisense2024,
  author = {Bingdongni},
  title = {OmniSense: Cross-Platform Data Intelligence and Insight System},
  year = {2024},
  url = {https://github.com/bingdongni/omnisense}
}
```

---

<div align="center">

**If this project helps you, please give it a ⭐️ Star!**

Made with ❤️ by [bingdongni](https://github.com/bingdongni)

</div>
