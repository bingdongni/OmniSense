# Google Scholar Spider - Quick Reference

## 快速开始

```python
import asyncio
from omnisense.spider.platforms.google_scholar import GoogleScholarSpider

async def main():
    spider = GoogleScholarSpider(headless=True)

    async with spider.session():
        # 搜索论文
        papers = await spider.search("machine learning", max_results=10)

        for paper in papers:
            print(f"{paper['title']} - {paper.get('citations_count', 0)} citations")

asyncio.run(main())
```

## 核心功能

### 🔍 Layer 1: Spider Layer (数据采集)
- ✅ 论文搜索（关键词、作者、年份）
- ✅ 作者主页信息
- ✅ 引用追踪
- ✅ 相关论文推荐
- ✅ 期刊/会议信息
- ✅ H-index计算

### 🛡️ Layer 2: Anti-Crawl Layer (反爬虫)
- ✅ reCAPTCHA自动检测和处理
- ✅ 请求延迟（2-5秒随机）
- ✅ User-Agent轮换（9种真实UA）
- ✅ Cookie管理和轮换
- ✅ IP代理支持
- ✅ 请求频率控制（60秒10次）
- ✅ 浏览器指纹伪装

### 🎯 Layer 3: Matcher Layer (过滤匹配)
- ✅ 引用数阈值过滤
- ✅ 年份范围过滤
- ✅ 期刊质量过滤
- ✅ 作者精确匹配
- ✅ 研究领域分类（10个领域）
- ✅ 开放获取过滤

### 📊 Layer 4: Interaction Layer (交互分析)
- ✅ 引用导出（BibTeX、RIS、EndNote）
- ✅ 相关论文推荐
- ✅ 引用网络分析
- ✅ 作者协作网络
- ✅ 论文影响力评估

## 代码统计

- **总行数**: 2091行
- **核心类**: GoogleScholarSpider
- **公共方法**: 30+
- **私有方法**: 20+
- **Layer 1方法**: 12个
- **Layer 2方法**: 8个
- **Layer 3方法**: 6个
- **Layer 4方法**: 4个

## 使用示例

### 示例1: 搜索和过滤
```python
# 搜索并过滤高质量论文
papers = await spider.search("deep learning", max_results=50, year_low=2020)
papers = spider.filter_by_citations(papers, min_citations=100)
papers = spider.filter_by_venue_quality(papers, quality_threshold=0.8)
```

### 示例2: 作者分析
```python
# 获取作者完整信息
profile = await spider.get_user_profile("user_id")
metrics = await spider.calculate_h_index("user_id")
network = await spider.build_collaboration_network("user_id", max_coauthors=20)
```

### 示例3: 论文影响力
```python
# 评估论文影响力
paper = await spider.get_post_detail("paper_id")
impact = await spider.assess_paper_impact(paper)
print(f"Impact Score: {impact['impact_score']}/100")
```

### 示例4: 引用导出
```python
# 导出多种格式
bibtex = await spider.export_citation(paper, format="bibtex")
ris = await spider.export_citation(paper, format="ris")
endnote = await spider.export_citation(paper, format="endnote")
```

## 高级配置

```python
# 使用代理和验证码服务
spider = GoogleScholarSpider(
    headless=True,
    proxy="http://proxy.example.com:8080",
    use_scholar_cn=True,  # 使用国内镜像
    captcha_api_key="YOUR_API_KEY"
)
```

## 反爬虫特性

### 自动处理
- ✅ 智能延迟（2-5秒）
- ✅ 频率限制（60秒/10次）
- ✅ UA自动轮换
- ✅ 指数退避重试

### CAPTCHA策略
1. 非headless模式：等待手动解决
2. 有API key：自动调用服务
3. 否则：切换身份重试

### 人类行为模拟
- 随机鼠标移动
- 随机页面滚动
- 阅读时间模拟

## 支持的浏览器
- Playwright（推荐）
- Chrome/Chromium
- Firefox
- Safari
- Edge

## 文档

完整文档请参考: `docs/google_scholar_spider_guide.md`

## 架构亮点

1. **模块化设计**: 4层架构清晰分离关注点
2. **可扩展性**: 基于BaseSpider，易于定制
3. **鲁棒性**: 完善的错误处理和重试机制
4. **智能化**: 自动反爬虫、缓存、过滤
5. **全面性**: 覆盖搜索、分析、导出全流程

## 注意事项

⚠️ **请遵守Google Scholar服务条款**
⚠️ **不要过度频繁请求**
⚠️ **建议使用代理轮换**
⚠️ **商业使用需获得授权**

## 版本信息

- Version: 2.0.0
- Date: 2026-01-14
- Author: OmniSense Team
- Lines: 2091

## License

遵循项目整体许可协议
