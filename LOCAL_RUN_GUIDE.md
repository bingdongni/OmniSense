# 🚀 OmniSense 本地运行指南

**环境要求**: ✅ Python 3.11.5 (已满足)

---

## 📋 目录

1. [快速开始](#快速开始) - 5分钟体验
2. [完整安装](#完整安装) - 完整功能
3. [最小化安装](#最小化安装) - 快速测试
4. [运行方式](#运行方式) - 三种界面
5. [常见问题](#常见问题)

---

## 🎯 快速开始（推荐初次使用）

### 步骤1: 安装最小化依赖（2-3分钟）

```bash
# 安装核心依赖（约30个包）
pip install -r requirements-minimal.txt
```

### 步骤2: 测试CLI工具

```bash
# 查看所有可用平台
python cli.py platforms

# 查看项目状态
python cli.py status

# 查看帮助
python cli.py --help
```

### 步骤3: 尝试数据采集（以微博为例）

```bash
# 搜索微博热点
python cli.py collect weibo --query "人工智能" --limit 10
```

---

## 🔧 完整安装（推荐生产使用）

### 方式1: 使用pip安装（10-15分钟）

```bash
# 安装所有依赖（约170个包，包含AI功能）
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

**注意**:
- PyTorch 需要约2GB磁盘空间
- 如果网络慢，可以使用国内镜像：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

### 方式2: 使用Docker（推荐，一键启动）

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看运行状态
docker-compose ps
```

Docker会自动启动：
- Web UI (Streamlit) - http://localhost:8501
- REST API (FastAPI) - http://localhost:8000
- Redis缓存
- MinIO对象存储

---

## 💡 最小化安装（适合快速测试）

如果您只想快速测试核心功能，无需AI Agent和Web UI：

```bash
# 仅安装核心爬虫依赖
pip install -r requirements-minimal.txt

# 测试基础功能
python -c "from omnisense import OmniSense; print('✓ Core OK')"
```

**最小化安装包含**:
- ✅ 所有51个平台的爬虫功能
- ✅ Cookie管理
- ✅ 基础数据处理
- ✅ CLI命令行工具
- ❌ 不包含Web UI
- ❌ 不包含API服务
- ❌ 不包含AI Agent

---

## 🎮 运行方式

### 方式1: CLI命令行（最简单）

```bash
# 1. 查看所有平台
python cli.py platforms

# 2. 搜索数据（以抖音为例）
python cli.py collect douyin --query "美食" --limit 20

# 3. 分析数据
python cli.py analyze --platform douyin --analysis-type sentiment

# 4. 导出数据
python cli.py export --platform douyin --format json --output results.json

# 5. 查看系统状态
python cli.py status
```

**CLI所有命令**:
```bash
python cli.py --help              # 查看所有命令
python cli.py platforms           # 查看51个平台列表
python cli.py collect             # 数据采集
python cli.py analyze             # 数据分析
python cli.py search              # 内容搜索
python cli.py match               # 内容匹配
python cli.py export              # 数据导出
python cli.py config              # 配置管理
python cli.py status              # 系统状态
```

### 方式2: Web UI界面（需完整安装）

```bash
# 启动Streamlit Web界面
streamlit run app.py

# 或者指定端口
streamlit run app.py --server.port 8501
```

浏览器访问: http://localhost:8501

**Web UI功能**:
- 📊 数据采集页面 - 可视化采集配置
- 🤖 智能分析页面 - 6个AI Agent协同分析
- 📈 数据可视化 - 图表、词云、网络图
- 📝 报告生成 - PDF/DOCX/HTML导出
- ⚙️ 系统设置 - 配置管理

### 方式3: REST API服务（需完整安装）

```bash
# 启动FastAPI服务
python api.py

# 或者使用uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

API文档:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**API端点示例**:
```bash
# 1. 健康检查
curl http://localhost:8000/api/v1/health

# 2. 数据采集
curl -X POST http://localhost:8000/api/v1/collect \
  -H "Content-Type: application/json" \
  -d '{"platform": "weibo", "query": "人工智能", "limit": 10}'

# 3. 查看结果
curl http://localhost:8000/api/v1/results/{task_id}
```

---

## 🧪 测试项目功能

### 测试1: 验证所有模块导入

```bash
# 运行验证脚本
python verify_installation.py
```

预期输出：
```
✓ Core modules OK
✓ 51 platform modules OK
✓ Multi-Agent system OK
✓ Cookie manager OK
✓ API client OK
```

### 测试2: 测试平台模块

```python
# 创建测试脚本 test_platform.py
from omnisense.spider.platforms.weibo import WeiboSpider

async def test_weibo():
    spider = WeiboSpider()
    # 不需要登录也可以搜索热门内容
    results = await spider.search("人工智能", limit=5)
    print(f"找到 {len(results)} 条微博")
    for post in results:
        print(f"- {post.get('text', '')[:50]}...")

# 运行
import asyncio
asyncio.run(test_weibo())
```

### 测试3: 测试Cookie管理

```python
from omnisense.auth import get_cookie_manager

# 创建Cookie管理器
cookie_mgr = get_cookie_manager()

# 从浏览器导入Cookie
cookies = cookie_mgr.import_from_browser("chrome", "weibo.com")
print(f"导入了 {len(cookies)} 个Cookie")

# 验证Cookie
is_valid = cookie_mgr.validate_cookies("weibo", cookies)
print(f"Cookie有效: {is_valid}")
```

### 测试4: 测试12个重点平台

```bash
# 创建测试脚本
python << 'EOF'
platforms = [
    "douyin", "xiaohongshu", "weibo", "tiktok",
    "kuaishou", "twitter", "github", "google_scholar",
    "youtube", "facebook", "instagram", "bilibili"
]

for platform in platforms:
    try:
        module = __import__(f"omnisense.spider.platforms.{platform}", fromlist=[f"{platform.title()}Spider"])
        print(f"✓ {platform:15s} - OK")
    except Exception as e:
        print(f"✗ {platform:15s} - {e}")
EOF
```

---

## 🎯 实战示例

### 示例1: 采集微博热搜

```bash
# 采集微博热搜前20条
python cli.py collect weibo --query "热搜" --limit 20 --sort hot

# 分析情感
python cli.py analyze --platform weibo --analysis-type sentiment

# 导出为Excel
python cli.py export --platform weibo --format excel --output weibo_hot.xlsx
```

### 示例2: GitHub趋势分析

```python
from omnisense.spider.platforms.github import GitHubSpider

async def analyze_trending():
    spider = GitHubSpider()

    # 获取Python趋势仓库
    trending = await spider.get_trending(language="python", since="daily")

    for repo in trending[:10]:
        print(f"⭐ {repo['stars']:6d} - {repo['name']}")
        print(f"   {repo['description'][:80]}")
        print()

import asyncio
asyncio.run(analyze_trending())
```

### 示例3: 学术论文搜索

```python
from omnisense.spider.platforms.google_scholar import GoogleScholarSpider

async def search_papers():
    spider = GoogleScholarSpider()

    # 搜索最新论文
    papers = await spider.search(
        query="machine learning",
        year_from=2024,
        limit=10
    )

    for paper in papers:
        print(f"📄 {paper['title']}")
        print(f"   引用数: {paper['citations']}")
        print(f"   作者: {', '.join(paper['authors'][:3])}")
        print()

import asyncio
asyncio.run(search_papers())
```

### 示例4: 多平台并行采集

```python
import asyncio
from omnisense import OmniSense

async def multi_platform_collect():
    client = OmniSense()

    # 并行采集多个平台
    tasks = [
        client.collect("weibo", query="AI", limit=10),
        client.collect("douyin", query="AI", limit=10),
        client.collect("xiaohongshu", query="AI", limit=10),
    ]

    results = await asyncio.gather(*tasks)

    for platform, data in zip(["微博", "抖音", "小红书"], results):
        print(f"{platform}: 采集到 {len(data)} 条数据")

asyncio.run(multi_platform_collect())
```

---

## ⚙️ 配置环境变量

创建 `.env` 文件（可选，用于API密钥等）：

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置（根据需要）
notepad .env  # Windows
# 或
nano .env     # Linux/Mac
```

**常用配置**:
```env
# 数据库
DATABASE_URL=sqlite:///data/omnisense.db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API密钥（可选，用于官方API）
GITHUB_TOKEN=your_github_token
YOUTUBE_API_KEY=your_youtube_key

# 代理（可选）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# 日志级别
LOG_LEVEL=INFO
```

---

## ❓ 常见问题

### Q1: 安装依赖时出错

**A**: 尝试以下解决方案：

```bash
# 1. 升级pip
python -m pip install --upgrade pip

# 2. 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 跳过失败的包
pip install -r requirements.txt --no-deps
pip install -r requirements.txt
```

### Q2: Playwright浏览器安装失败

**A**: 使用镜像加速：

```bash
# Windows (PowerShell)
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/"
playwright install chromium

# Linux/Mac
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
playwright install chromium
```

### Q3: 运行时提示找不到模块

**A**: 确保在项目根目录运行：

```bash
# 查看当前目录
pwd  # Linux/Mac
cd   # Windows

# 应该在: c:\Users\29051\Desktop\聚析_OmniSense

# 添加到Python路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;%cd%          # Windows CMD
$env:PYTHONPATH += ";$(Get-Location)"     # Windows PowerShell
```

### Q4: 采集数据时被反爬虫拦截

**A**: 使用Cookie或代理：

```bash
# 方式1: 从浏览器导入Cookie
python -c "
from omnisense.auth import get_cookie_manager
mgr = get_cookie_manager()
mgr.import_from_browser('chrome', 'weibo.com')
"

# 方式2: 配置代理
export HTTP_PROXY=http://127.0.0.1:7890
```

### Q5: Web UI无法启动

**A**: 检查端口占用：

```bash
# Windows
netstat -ano | findstr :8501

# Linux/Mac
lsof -i :8501

# 使用其他端口
streamlit run app.py --server.port 8502
```

### Q6: 内存不足

**A**: 使用最小化安装：

```bash
# 1. 仅安装核心依赖
pip install -r requirements-minimal.txt

# 2. 不安装PyTorch（如果不需要AI功能）
pip install -r requirements.txt --no-deps
pip install $(grep -v torch requirements.txt)
```

---

## 🎉 推荐运行流程

### 首次使用（5分钟快速体验）

1. **安装最小依赖**
   ```bash
   pip install -r requirements-minimal.txt
   ```

2. **测试CLI**
   ```bash
   python cli.py platforms
   python cli.py status
   ```

3. **采集数据**
   ```bash
   python cli.py collect weibo --query "科技" --limit 5
   ```

4. **查看结果**
   ```bash
   cat data/weibo/*.json  # Linux/Mac
   type data\weibo\*.json  # Windows
   ```

### 深度使用（完整功能）

1. **完整安装**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **配置环境**
   ```bash
   cp .env.example .env
   # 编辑 .env 添加API密钥
   ```

3. **启动Web UI**
   ```bash
   streamlit run app.py
   ```

4. **启动API服务**
   ```bash
   python api.py
   ```

5. **使用Multi-Agent分析**
   - 在Web UI中上传数据
   - 选择6个Agent进行智能分析
   - 生成PDF报告

---

## 📊 性能优化建议

### 提升采集速度

```python
# 配置并发数
from omnisense.config import settings

settings.MAX_CONCURRENT_REQUESTS = 10  # 增加并发（默认5）
settings.REQUEST_DELAY = 0.5           # 减少延迟（默认1秒）
```

### 减少内存占用

```python
# 使用流式处理
from omnisense import OmniSense

client = OmniSense()
async for batch in client.collect_stream("weibo", query="AI", batch_size=100):
    # 处理批次数据
    process_batch(batch)
    # 数据会自动释放
```

### 使用缓存

```python
# 启用Redis缓存
settings.ENABLE_CACHE = True
settings.CACHE_TTL = 3600  # 缓存1小时
```

---

## 🎯 下一步

1. ✅ **基础测试** - 验证安装和核心功能
2. ✅ **数据采集** - 尝试采集各个平台数据
3. ✅ **功能探索** - 测试Cookie管理、API集成
4. ✅ **深度使用** - 使用Multi-Agent分析
5. ✅ **生产部署** - Docker部署到服务器

---

## 📚 相关文档

- [README.md](README.md) - 项目介绍
- [QUICK_START.md](QUICK_START.md) - 快速开始
- [docs/api.md](docs/api.md) - API文档
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - 部署指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

---

## 🆘 获取帮助

如果遇到问题：

1. 查看 [常见问题](#常见问题) 章节
2. 查看项目文档
3. 在GitHub提Issue
4. 查看日志: `logs/omnisense.log`

---

**祝您使用愉快！🎉**

**项目地址**: https://github.com/USERNAME/OmniSense
**创建日期**: 2026-01-14
