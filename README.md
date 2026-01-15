# 聚析 OmniSense

<div align="center">

![OmniSense Logo](docs/images/logo.png)

**全域数据智能洞察平台 | Cross-Platform Data Intelligence & Insight System**

[![GitHub Stars](https://img.shields.io/github/stars/bingdongni/omnisense?style=social)](https://github.com/bingdongni/omnisense)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-supported-brightgreen)](Dockerfile)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

## 📋 项目简介

聚析（OmniSense）是一个强大的**全域数据智能洞察平台**，为50个主流平台提供独立定制的数据采集、反反爬、内容匹配、互动处理全链路机制。通过多Agent协作系统，实现从数据采集到智能分析的端到端自动化。

### 核心特性

- 🌐 **50平台独立机制** - 每个平台独立定制爬取、反爬、匹配、互动处理机制
- 🤖 **多Agent协作** - Scout、Analyst、Ecommerce、Academic、Creator、Report六大智能体
- 🛡️ **强大反爬系统** - 智能IP池、指纹伪装、验证码处理、行为模拟
- 🎯 **精准内容匹配** - 基于BERT的语义分析+SimHash去重+FAISS向量检索
- 💬 **互动数据处理** - 评论链采集、情感分析、热点提取、关系图谱
- 📊 **可视化分析** - ECharts图表+词云+网络图谱+多维度数据展示
- 🚀 **零门槛部署** - Docker一键部署+Web UI+桌面GUI+CLI工具
- 🔧 **高度可扩展** - 模块化设计，支持快速新增平台和功能

### 支持平台矩阵

| 类别 | 平台 (共50个) |
|------|---------------|
| **短视频** | 抖音、快手、TikTok、YouTube、Bilibili |
| **社交媒体** | 微博、小红书、脉脉、Twitter(X)、Facebook、Instagram、LinkedIn、Reddit |
| **内容社区** | 微信公众号、微信视频号、知乎、豆瓣、虎扑、百度贴吧、今日头条、搜狐、汽车之家/懂车帝、雪球、Quora、Medium |
| **跨境电商** | Amazon、Temu、Shopee、Ozon、淘宝、天猫、京东、拼多多、闲鱼、得物、唯品会 |
| **本地生活** | 美团、大众点评 |
| **日常回收** | 转转、爱回收 |
| **搜索引擎** | 百度、Google、夸克 |
| **学术平台** | Google Scholar、CNKI、Web of Science、arXiv |
| **开发者社区** | GitHub、CSDN、Stack Overflow |

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/bingdongni/omnisense.git
cd omnisense

# 启动服务
docker-compose up -d

# 访问 Web UI
open http://localhost:8501
```

### 方式二：本地安装

```bash
# 克隆项目
git clone https://github.com/bingdongni/omnisense.git
cd omnisense

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 启动 Web UI
streamlit run app.py

# 或使用 CLI
python cli.py --help
```

### 快速示例

```python
from omnisense import OmniSense

# 初始化
omni = OmniSense()

# 抖音视频采集与分析
result = omni.collect(
    platform="douyin",
    keyword="AI编程",
    max_count=100
)

# 智能分析
analysis = omni.analyze(
    data=result,
    agents=["analyst", "creator"]
)

# 生成报告
omni.generate_report(
    analysis=analysis,
    format="pdf",
    output="report.pdf"
)
```

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层                            │
│              Streamlit Web + PyQt5 GUI + CLI             │
├─────────────────────────────────────────────────────────┤
│                    报告生成层                            │
│           Jinja2模板 + WeasyPrint PDF + Word输出         │
├─────────────────────────────────────────────────────────┤
│                    可视化层                              │
│              ECharts + Plotly + 词云 + 网络图谱          │
├─────────────────────────────────────────────────────────┤
│                    智能分析层                            │
│           多Agent协作系统 (LangChain + Ollama)           │
├─────────────────────────────────────────────────────────┤
│                    互动处理层                            │
│           49平台独立互动引擎 + 情感分析               │
├─────────────────────────────────────────────────────────┤
│                    智能匹配层                            │
│           49平台独立匹配引擎 + BERT语义分析              │
├─────────────────────────────────────────────────────────┤
│                    数据存储层                            │
│           SQLite + ChromaDB + Redis + MinIO              │
├─────────────────────────────────────────────────────────┤
│                    数据爬取层                            │
│           49平台独立爬取引擎 + Playwright                │
├─────────────────────────────────────────────────────────┤
│                    反反爬层                              │
│           IP池 + 指纹伪装 + 验证码处理                   │
└─────────────────────────────────────────────────────────┘
```

## 📚 核心功能

### 1. 数据采集

- ✅ 49个平台独立爬取机制
- ✅ 多线程/异步并发采集
- ✅ 智能去重与增量更新
- ✅ 媒体文件自动下载
- ✅ 实时进度监控

### 2. 反反爬系统

- ✅ 智能IP池轮换
- ✅ 浏览器指纹伪装
- ✅ 自动验证码处理
- ✅ 人类行为模拟
- ✅ Cookie池管理

### 3. 内容匹配

- ✅ 多模态语义理解
- ✅ 相似度去重
- ✅ 向量检索匹配
- ✅ 热度加权排序
- ✅ 标签智能分类

### 4. 互动分析

- ✅ 评论链深度采集
- ✅ 情感倾向分析
- ✅ 热点关键词提取
- ✅ 用户画像构建
- ✅ 传播路径追踪

### 5. 智能Agent

| Agent | 功能 |
|-------|------|
| 🔍 Scout | 全域数据探索、热点发现、趋势追踪 |
| 📊 Analyst | 情感分析、话题聚类、竞品对比 |
| 🛒 Ecommerce | 选品分析、价格监控、评价分析 |
| 📚 Academic | 文献检索、引用分析、知识图谱 |
| ✨ Creator | 爆款分析、选题推荐、标题优化 |
| 📄 Report | 多模板、多格式报告生成 |

### 6. 数据可视化

- ✅ 交互式图表（折线图、柱状图、饼图）
- ✅ 词云图
- ✅ 社交网络图谱
- ✅ 地理热力图
- ✅ 时间序列分析

## 🎯 应用场景

### 内容创作者

- 爆款内容分析
- 选题趋势追踪
- 竞品监控分析
- 粉丝互动洞察

### 跨境电商

- 选品数据分析
- 竞品价格监控
- 评价情感分析
- 市场趋势预测

### 学术研究

- 文献批量检索
- 引用关系分析
- 研究趋势追踪
- 综述自动生成

### 市场研究

- 跨平台舆情监控
- 品牌声量分析
- 消费者洞察
- 行业趋势报告

### 开发者

- 技术趋势分析
- 开源项目监控
- 社区热度追踪
- 技术栈选型

## 📖 文档

- [快速开始](docs/quick_start.md)
- [平台使用指南](docs/platforms/)
- [开发者指南](docs/developer_guide.md)
- [API 文档](docs/api.md)
- [常见问题](docs/faq.md)
- [贡献指南](CONTRIBUTING.md)

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| 核心语言 | Python 3.11+ |
| Web框架 | Streamlit, FastAPI |
| 爬虫 | Playwright, aiohttp, Requests |
| 反反爬 | ProxyPool, FingerprintSwitcher |
| NLP | BERT, sentence-transformers |
| Agent | LangChain, Ollama |
| 数据库 | SQLite, ChromaDB, Redis |
| 存储 | MinIO |
| 可视化 | ECharts, Plotly, WordCloud |
| 部署 | Docker, Docker Compose |

## 🤝 贡献

我们欢迎所有形式的贡献！请查看 [贡献指南](CONTRIBUTING.md) 了解详情。

### 贡献者激励

- 🏆 核心贡献者署名展示
- 💎 免费 Pro 版订阅
- 📚 技术曝光机会
- 🎁 定制周边礼品

### 当前贡献者

<a href="https://github.com/bingdongni/omnisense/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bingdongni/omnisense" />
</a>

## 📊 项目统计

![Alt](https://repobeats.axiom.co/api/embed/your-repo-id.svg "Repobeats analytics image")

## 📜 开源协议

本项目基于 [MIT License](LICENSE) 开源。

## ⚠️ 免责声明

1. 本项目仅用于学习研究，严禁用于非法用途
2. 仅采集互联网公开数据，不采集私密信息
3. 使用前请遵守目标平台用户协议和 robots.txt
4. 用户需自行承担使用本项目的法律责任

## 💬 联系方式

- GitHub Issues: [提交问题](https://github.com/bingdongni/omnisense/issues)
- GitHub Discussions: [参与讨论](https://github.com/bingdongni/omnisense/discussions)
- Email: bingdongni@example.com

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=bingdongni/omnisense&type=Date)](https://star-history.com/#bingdongni/omnisense&Date)

## 📝 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新历史。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

Made with ❤️ by [bingdongni](https://github.com/bingdongni)

</div>
