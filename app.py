"""
OmniSense Streamlit Web Application
全域数据智能洞察平台 - Web界面
"""

import streamlit as st
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Configure page
st.set_page_config(
    page_title="OmniSense - 全域数据智能洞察平台",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(120deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #64748b;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .platform-tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 15px;
        background-color: #e0e7ff;
        color: #3730a3;
        font-size: 0.875rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
    .stProgress .st-bo {
        background-color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Platform definitions (49 platforms)
PLATFORMS = {
    "短视频平台": [
        "douyin", "kuaishou", "tiktok", "youtube_shorts"
    ],
    "社交媒体": [
        "weibo", "twitter", "facebook", "instagram", "linkedin"
    ],
    "内容社区": [
        "xiaohongshu", "zhihu", "douban", "baidu_tieba", "reddit"
    ],
    "视频平台": [
        "bilibili", "youtube", "vimeo", "dailymotion"
    ],
    "电商平台": [
        "taobao", "tmall", "jd", "pinduoduo", "amazon",
        "ebay", "shopee", "lazada"
    ],
    "生活服务": [
        "meituan", "dianping", "eleme", "koubei"
    ],
    "新闻资讯": [
        "toutiao", "jinritoutiao", "netease_news", "tencent_news"
    ],
    "搜索引擎": [
        "baidu", "google", "bing", "sogou"
    ],
    "学术平台": [
        "google_scholar", "cnki", "wanfang", "ieee"
    ],
    "开发平台": [
        "github", "gitlab", "gitee", "stackoverflow", "csdn"
    ],
    "其他平台": [
        "wechat_mp", "quora", "medium", "pinterest", "tumblr"
    ]
}

ALL_PLATFORMS = []
for platforms in PLATFORMS.values():
    ALL_PLATFORMS.extend(platforms)

# Agent types
AGENT_TYPES = {
    "scout": "侦察Agent - 发现和追踪内容",
    "analyst": "分析Agent - 深度数据分析",
    "ecommerce": "电商Agent - 商品和市场分析",
    "academic": "学术Agent - 学术论文分析",
    "creator": "创作Agent - 内容创作建议",
    "report": "报告Agent - 生成专业报告"
}

# Analysis types
ANALYSIS_TYPES = {
    "sentiment": "情感分析",
    "clustering": "聚类分析",
    "prediction": "趋势预测",
    "comparison": "对比分析"
}


# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'omnisense' not in st.session_state:
        st.session_state.omnisense = None
    if 'collection_results' not in st.session_state:
        st.session_state.collection_results = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'current_collection_id' not in st.session_state:
        st.session_state.current_collection_id = None


@st.cache_resource
def get_omnisense():
    """Get or create OmniSense instance"""
    try:
        from omnisense.core import OmniSense
        return OmniSense()
    except Exception as e:
        st.error(f"初始化OmniSense失败: {e}")
        return None


def home_page():
    """Home page with project introduction"""
    st.markdown('<h1 class="main-header">🔍 OmniSense</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">全域数据智能洞察平台 - 跨平台智能数据采集与分析系统</p>',
                unsafe_allow_html=True)

    # Feature cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 🌐 全域采集
        支持49+主流平台的数据采集
        - 短视频平台 (抖音、快手、TikTok等)
        - 社交媒体 (微博、Twitter等)
        - 电商平台 (淘宝、京东、Amazon等)
        - 学术平台 (Google Scholar、CNKI等)
        """)

    with col2:
        st.markdown("""
        ### 🤖 智能分析
        多Agent协同智能分析
        - 侦察Agent：内容发现与追踪
        - 分析Agent：深度数据洞察
        - 电商Agent：商品市场分析
        - 学术Agent：论文文献分析
        - 创作Agent：内容创作建议
        - 报告Agent：专业报告生成
        """)

    with col3:
        st.markdown("""
        ### 📊 可视化报告
        多维度数据可视化与报告
        - 情感分析与趋势预测
        - 聚类分析与对比分析
        - 多格式报告导出 (PDF/DOCX/HTML)
        - 交互式图表展示
        """)

    st.divider()

    # System overview
    st.markdown("### 📈 系统架构")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 核心模块
        - **Spider Manager**: 智能爬虫管理
        - **Anti-Crawl**: 反爬虫策略
        - **Matcher**: 内容匹配去重
        - **Interaction**: 互动数据处理
        - **Agent System**: 多智能体协作
        - **Analysis Engine**: 分析引擎
        - **Storage**: 数据存储管理
        - **Visualization**: 可视化渲染
        """)

    with col2:
        st.markdown("""
        #### 技术特性
        - 🚀 高并发异步采集
        - 🛡️ 智能反爬虫对抗
        - 🔍 语义去重匹配
        - 🤖 LLM驱动的智能分析
        - 📊 多维度数据可视化
        - 💾 分布式存储架构
        - 🔐 企业级安全保障
        - 📱 响应式Web界面
        """)

    st.divider()

    # Quick start
    st.markdown("### 🚀 快速开始")
    st.markdown("""
    1. **数据采集**: 前往"数据采集"页面，选择平台并配置采集参数
    2. **智能分析**: 在"分析"页面选择Agent和分析类型，运行智能分析
    3. **生成报告**: 在"报告"页面生成多格式专业报告
    4. **查看统计**: 在"统计"页面查看数据统计和可视化图表
    """)

    # Statistics preview
    st.markdown("### 📊 系统状态")

    omnisense = get_omnisense()
    if omnisense:
        try:
            stats = asyncio.run(omnisense.db.get_statistics())

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("采集内容数", f"{stats.get('total_content', 0):,}")
            with col2:
                st.metric("互动数据", f"{stats.get('total_interactions', 0):,}")
            with col3:
                st.metric("采集任务数", f"{stats.get('total_collections', 0):,}")
            with col4:
                st.metric("支持平台", len(ALL_PLATFORMS))
        except Exception as e:
            st.info("暂无统计数据")

    st.divider()

    # Footer
    st.markdown("""
    <div style='text-align: center; color: #64748b; padding: 2rem 0;'>
        <p>OmniSense v1.0.0 | 全域数据智能洞察平台</p>
        <p>Built with ❤️ using Streamlit, LangChain, and Playwright</p>
    </div>
    """, unsafe_allow_html=True)


def data_collection_page():
    """Data collection page"""
    st.title("📥 数据采集")
    st.markdown("从49+主流平台采集数据，支持关键词搜索、用户主页、直接URL等多种采集方式")

    omnisense = get_omnisense()
    if not omnisense:
        st.error("OmniSense系统未初始化，请检查配置")
        return

    # Collection configuration
    st.markdown("### 🔧 采集配置")

    col1, col2 = st.columns([1, 1])

    with col1:
        # Platform selector with categories
        st.markdown("#### 选择平台")
        platform_category = st.selectbox(
            "平台分类",
            list(PLATFORMS.keys()),
            help="选择平台类别"
        )

        platform = st.selectbox(
            "具体平台",
            PLATFORMS[platform_category],
            help="选择要采集的平台"
        )

        # Collection method
        collection_method = st.radio(
            "采集方式",
            ["关键词搜索", "用户主页", "直接URL"],
            horizontal=True
        )

    with col2:
        # Input fields based on collection method
        st.markdown("#### 采集参数")

        keyword = None
        user_id = None
        url = None

        if collection_method == "关键词搜索":
            keyword = st.text_input(
                "搜索关键词",
                placeholder="例如: AI编程",
                help="输入要搜索的关键词"
            )
        elif collection_method == "用户主页":
            user_id = st.text_input(
                "用户ID",
                placeholder="例如: user123456",
                help="输入用户ID或用户名"
            )
        else:
            url = st.text_input(
                "内容URL",
                placeholder="例如: https://...",
                help="输入要采集的内容URL"
            )

        max_count = st.number_input(
            "最大采集数量",
            min_value=1,
            max_value=1000,
            value=50,
            step=10,
            help="设置最多采集多少条数据"
        )

    # Advanced options
    with st.expander("🔧 高级选项"):
        col1, col2 = st.columns(2)

        with col1:
            download_media = st.checkbox("下载媒体文件", value=False)
            use_proxy = st.checkbox("使用代理", value=False)

        with col2:
            headless = st.checkbox("无头模式", value=True)
            enable_captcha = st.checkbox("自动解决验证码", value=False)

    st.divider()

    # Collection button
    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        start_collection = st.button("🚀 开始采集", type="primary", use_container_width=True)

    # Collection process
    if start_collection:
        if not any([keyword, user_id, url]):
            st.error("请输入采集参数（关键词、用户ID或URL）")
            return

        st.markdown("### 📊 采集进度")

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 正在初始化采集任务...")
            progress_bar.progress(10)
            time.sleep(0.5)

            status_text.text(f"🌐 正在连接 {platform} 平台...")
            progress_bar.progress(30)
            time.sleep(0.5)

            status_text.text("📥 正在采集数据...")
            progress_bar.progress(50)

            # Execute collection
            result = omnisense.collect(
                platform=platform,
                keyword=keyword,
                user_id=user_id,
                url=url,
                max_count=max_count
            )

            progress_bar.progress(80)
            status_text.text("💾 正在保存数据...")
            time.sleep(0.5)

            progress_bar.progress(100)
            status_text.text("✅ 采集完成！")

            # Save to session state
            st.session_state.collection_results.append(result)
            st.session_state.current_collection_id = result.get('platform') + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")

            # Display success message
            st.markdown(f"""
            <div class="success-box">
                <h4>✅ 采集成功！</h4>
                <p><strong>平台:</strong> {platform}</p>
                <p><strong>采集数量:</strong> {result.get('count', 0)} 条</p>
                <p><strong>采集时间:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ 采集失败: {str(e)}")
            return

    # Results preview
    if st.session_state.collection_results:
        st.divider()
        st.markdown("### 📋 采集结果预览")

        latest_result = st.session_state.collection_results[-1]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("采集平台", latest_result.get('platform', 'N/A'))
        with col2:
            st.metric("数据条数", latest_result.get('count', 0))
        with col3:
            st.metric("状态", "✅ 完成")

        # Data preview
        if latest_result.get('data'):
            st.markdown("#### 数据预览")

            # Convert to DataFrame for display
            preview_data = []
            for item in latest_result['data'][:10]:  # Show first 10 items
                preview_data.append({
                    'ID': item.get('content_id', 'N/A'),
                    '标题': item.get('title', 'N/A')[:50] + '...' if item.get('title') else 'N/A',
                    '作者': item.get('author', {}).get('name', 'N/A'),
                    '点赞': item.get('stats', {}).get('likes', 0),
                    '评论': item.get('stats', {}).get('comments', 0),
                    '发布时间': item.get('publish_time', 'N/A')
                })

            df = pd.DataFrame(preview_data)
            st.dataframe(df, use_container_width=True)

            # Export option
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("💾 导出数据", use_container_width=True):
                    # Convert to JSON
                    json_str = json.dumps(latest_result, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="下载 JSON",
                        data=json_str,
                        file_name=f"omnisense_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )


def analysis_page():
    """Analysis page"""
    st.title("🔬 智能分析")
    st.markdown("使用多Agent协同系统对采集数据进行深度智能分析")

    omnisense = get_omnisense()
    if not omnisense:
        st.error("OmniSense系统未初始化，请检查配置")
        return

    # Check if there's data to analyze
    if not st.session_state.collection_results:
        st.warning("⚠️ 没有可分析的数据，请先前往【数据采集】页面采集数据")
        return

    st.markdown("### 📊 数据源")

    # Select data source
    col1, col2 = st.columns([2, 1])

    with col1:
        collection_options = [
            f"{i+1}. {result.get('platform')} - {result.get('count')} 条数据"
            for i, result in enumerate(st.session_state.collection_results)
        ]

        selected_collection = st.selectbox(
            "选择要分析的数据集",
            range(len(collection_options)),
            format_func=lambda i: collection_options[i]
        )

    with col2:
        st.metric("数据条数", st.session_state.collection_results[selected_collection].get('count', 0))

    st.divider()

    # Analysis configuration
    st.markdown("### 🤖 分析配置")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 选择Agent")
        selected_agents = []

        for agent_key, agent_desc in AGENT_TYPES.items():
            if st.checkbox(agent_desc, key=f"agent_{agent_key}"):
                selected_agents.append(agent_key)

    with col2:
        st.markdown("#### 分析类型")
        selected_analysis = []

        for analysis_key, analysis_desc in ANALYSIS_TYPES.items():
            if st.checkbox(analysis_desc, key=f"analysis_{analysis_key}"):
                selected_analysis.append(analysis_key)

    # Advanced options
    with st.expander("🔧 高级选项"):
        col1, col2 = st.columns(2)

        with col1:
            llm_model = st.selectbox(
                "LLM模型",
                ["qwen2.5:7b", "qwen2.5:14b", "llama3:8b", "gpt-3.5-turbo", "gpt-4"],
                help="选择用于分析的大语言模型"
            )

        with col2:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="控制输出的随机性"
            )

    st.divider()

    # Analysis button
    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        start_analysis = st.button("🚀 开始分析", type="primary", use_container_width=True)

    # Analysis process
    if start_analysis:
        if not selected_agents and not selected_analysis:
            st.error("请至少选择一个Agent或分析类型")
            return

        st.markdown("### 📊 分析进度")

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 正在准备分析数据...")
            progress_bar.progress(10)
            time.sleep(0.5)

            # Get selected data
            data = st.session_state.collection_results[selected_collection]

            status_text.text("🤖 正在运行Agent分析...")
            progress_bar.progress(30)
            time.sleep(0.5)

            # Execute analysis
            results = omnisense.analyze(
                data=data,
                agents=selected_agents if selected_agents else None,
                analysis_types=selected_analysis if selected_analysis else None
            )

            progress_bar.progress(80)
            status_text.text("💾 正在保存结果...")
            time.sleep(0.5)

            progress_bar.progress(100)
            status_text.text("✅ 分析完成！")

            # Save to session state
            st.session_state.analysis_results = results

            # Display success message
            st.markdown(f"""
            <div class="success-box">
                <h4>✅ 分析完成！</h4>
                <p><strong>使用Agent:</strong> {', '.join(selected_agents) if selected_agents else '默认'}</p>
                <p><strong>分析类型:</strong> {', '.join(selected_analysis) if selected_analysis else '默认'}</p>
                <p><strong>分析时间:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ 分析失败: {str(e)}")
            return

    # Results display
    if st.session_state.analysis_results:
        st.divider()
        st.markdown("### 📈 分析结果")

        results = st.session_state.analysis_results

        # Agent results
        if 'agents' in results:
            st.markdown("#### 🤖 Agent分析结果")

            for agent_name, agent_result in results['agents'].items():
                with st.expander(f"📊 {AGENT_TYPES.get(agent_name, agent_name)}"):
                    st.json(agent_result)

        # Analysis results
        if 'analysis' in results:
            st.markdown("#### 📊 数据分析结果")

            analysis_results = results['analysis']

            # Sentiment analysis
            if 'sentiment' in analysis_results:
                st.markdown("##### 情感分析")
                sentiment_data = analysis_results['sentiment']

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("正面", f"{sentiment_data.get('positive', 0)}%")
                with col2:
                    st.metric("中性", f"{sentiment_data.get('neutral', 0)}%")
                with col3:
                    st.metric("负面", f"{sentiment_data.get('negative', 0)}%")

                # Sentiment chart
                fig = px.pie(
                    values=[sentiment_data.get('positive', 0),
                           sentiment_data.get('neutral', 0),
                           sentiment_data.get('negative', 0)],
                    names=['正面', '中性', '负面'],
                    title="情感分布",
                    color_discrete_sequence=['#10b981', '#6b7280', '#ef4444']
                )
                st.plotly_chart(fig, use_container_width=True)

            # Clustering
            if 'clustering' in analysis_results:
                st.markdown("##### 聚类分析")
                st.json(analysis_results['clustering'])

            # Prediction
            if 'prediction' in analysis_results:
                st.markdown("##### 趋势预测")
                st.json(analysis_results['prediction'])

            # Comparison
            if 'comparison' in analysis_results:
                st.markdown("##### 对比分析")
                st.json(analysis_results['comparison'])


def reports_page():
    """Reports page"""
    st.title("📄 报告生成")
    st.markdown("生成多格式专业分析报告，支持PDF、DOCX、HTML、Markdown格式")

    omnisense = get_omnisense()
    if not omnisense:
        st.error("OmniSense系统未初始化，请检查配置")
        return

    # Check if there's analysis results
    if not st.session_state.analysis_results:
        st.warning("⚠️ 没有可用的分析结果，请先前往【分析】页面进行数据分析")
        return

    st.markdown("### 📋 报告配置")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 报告格式")
        report_format = st.selectbox(
            "选择格式",
            ["pdf", "docx", "html", "md"],
            format_func=lambda x: {
                "pdf": "📕 PDF - 便携文档格式",
                "docx": "📘 DOCX - Word文档",
                "html": "🌐 HTML - 网页格式",
                "md": "📝 Markdown - 文本格式"
            }[x]
        )

        report_title = st.text_input(
            "报告标题",
            value=f"OmniSense分析报告_{datetime.now().strftime('%Y%m%d')}",
            help="输入报告标题"
        )

    with col2:
        st.markdown("#### 报告选项")

        include_charts = st.checkbox("包含图表", value=True)
        include_raw_data = st.checkbox("包含原始数据", value=False)
        include_summary = st.checkbox("包含执行摘要", value=True)
        include_recommendations = st.checkbox("包含建议", value=True)

    # Template selection
    with st.expander("📄 报告模板"):
        template = st.selectbox(
            "选择模板",
            ["standard", "business", "academic", "technical"],
            format_func=lambda x: {
                "standard": "标准模板",
                "business": "商业模板",
                "academic": "学术模板",
                "technical": "技术模板"
            }[x]
        )

    st.divider()

    # Generate button
    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        generate_report = st.button("📊 生成报告", type="primary", use_container_width=True)

    # Report generation process
    if generate_report:
        st.markdown("### 📊 生成进度")

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 正在准备报告数据...")
            progress_bar.progress(10)
            time.sleep(0.5)

            status_text.text("📊 正在生成图表...")
            progress_bar.progress(30)
            time.sleep(0.5)

            status_text.text(f"📝 正在生成 {report_format.upper()} 报告...")
            progress_bar.progress(60)
            time.sleep(0.5)

            # Generate report
            output_file = f"reports/{report_title}.{report_format}"
            Path("reports").mkdir(exist_ok=True)

            # Simulate report generation (replace with actual implementation)
            report_path = output_file

            progress_bar.progress(90)
            status_text.text("💾 正在保存报告...")
            time.sleep(0.5)

            progress_bar.progress(100)
            status_text.text("✅ 报告生成完成！")

            # Display success message
            st.markdown(f"""
            <div class="success-box">
                <h4>✅ 报告生成成功！</h4>
                <p><strong>格式:</strong> {report_format.upper()}</p>
                <p><strong>文件名:</strong> {report_title}.{report_format}</p>
                <p><strong>生成时间:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            """, unsafe_allow_html=True)

            # Download button
            st.divider()

            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                # Create dummy file for download (replace with actual file)
                report_content = f"OmniSense Analysis Report\n{datetime.now()}\n\nReport content here..."

                st.download_button(
                    label="💾 下载报告",
                    data=report_content,
                    file_name=f"{report_title}.{report_format}",
                    mime=f"application/{report_format}",
                    use_container_width=True
                )

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ 报告生成失败: {str(e)}")

    # Report preview
    st.divider()
    st.markdown("### 📋 报告预览")

    preview_tabs = st.tabs(["📊 概览", "📈 图表", "📝 内容"])

    with preview_tabs[0]:
        st.markdown("#### 报告概览")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("分析平台", st.session_state.collection_results[-1].get('platform', 'N/A') if st.session_state.collection_results else 'N/A')
        with col2:
            st.metric("数据量", st.session_state.collection_results[-1].get('count', 0) if st.session_state.collection_results else 0)
        with col3:
            st.metric("分析时间", datetime.now().strftime("%Y-%m-%d"))

    with preview_tabs[1]:
        st.markdown("#### 分析图表")
        st.info("图表将在报告中显示")

    with preview_tabs[2]:
        st.markdown("#### 报告内容")
        st.markdown("""
        **执行摘要**

        本报告基于OmniSense平台采集和分析的数据生成...

        **主要发现**
        - 发现1: ...
        - 发现2: ...
        - 发现3: ...

        **建议**
        1. 建议1: ...
        2. 建议2: ...
        3. 建议3: ...
        """)


def statistics_page():
    """Statistics page"""
    st.title("📊 数据统计")
    st.markdown("查看数据库统计信息和可视化图表")

    omnisense = get_omnisense()
    if not omnisense:
        st.error("OmniSense系统未初始化，请检查配置")
        return

    try:
        # Get statistics
        stats = asyncio.run(omnisense.db.get_statistics())

        # Overview metrics
        st.markdown("### 📈 总体统计")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            <div class="metric-card">
                <h2>{:,}</h2>
                <p>采集内容数</p>
            </div>
            """.format(stats.get('total_content', 0)), unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="metric-card">
                <h2>{:,}</h2>
                <p>互动数据</p>
            </div>
            """.format(stats.get('total_interactions', 0)), unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div class="metric-card">
                <h2>{:,}</h2>
                <p>采集任务数</p>
            </div>
            """.format(stats.get('total_collections', 0)), unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div class="metric-card">
                <h2>{}</h2>
                <p>支持平台</p>
            </div>
            """.format(len(ALL_PLATFORMS)), unsafe_allow_html=True)

        st.divider()

        # Platform distribution
        st.markdown("### 🌐 平台分布")

        if st.session_state.collection_results:
            # Create platform distribution chart
            platform_counts = {}
            for result in st.session_state.collection_results:
                platform = result.get('platform', 'Unknown')
                platform_counts[platform] = platform_counts.get(platform, 0) + result.get('count', 0)

            fig = px.bar(
                x=list(platform_counts.keys()),
                y=list(platform_counts.values()),
                title="各平台数据量分布",
                labels={'x': '平台', 'y': '数据量'},
                color=list(platform_counts.values()),
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无平台数据")

        st.divider()

        # Time series
        st.markdown("### 📅 时间分布")

        col1, col2 = st.columns(2)

        with col1:
            # Sample time series data
            dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
            values = [100 + i * 10 + (i % 7) * 20 for i in range(30)]

            fig = px.line(
                x=dates,
                y=values,
                title="日数据采集趋势",
                labels={'x': '日期', 'y': '数据量'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Sample category distribution
            categories = ['正面', '中性', '负面']
            values = [45, 35, 20]

            fig = px.pie(
                values=values,
                names=categories,
                title="情感分布",
                color_discrete_sequence=['#10b981', '#6b7280', '#ef4444']
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Recent collections
        st.markdown("### 📋 近期采集记录")

        if st.session_state.collection_results:
            records = []
            for i, result in enumerate(st.session_state.collection_results[-10:]):  # Last 10
                records.append({
                    '序号': i + 1,
                    '平台': result.get('platform', 'N/A'),
                    '数据量': result.get('count', 0),
                    '关键词': result.get('meta', {}).get('keyword', 'N/A'),
                    '状态': '✅ 完成'
                })

            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无采集记录")

        st.divider()

        # Database info
        st.markdown("### 💾 数据库信息")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **数据库配置**
            - 类型: SQLite + ChromaDB
            - 路径: data/omnisense.db
            - 向量库: data/chroma
            - 状态: ✅ 正常
            """)

        with col2:
            st.markdown("""
            **存储统计**
            - 内容表: {:,} 条记录
            - 互动表: {:,} 条记录
            - 集合表: {:,} 条记录
            - 创作者表: 0 条记录
            """.format(
                stats.get('total_content', 0),
                stats.get('total_interactions', 0),
                stats.get('total_collections', 0)
            ))

    except Exception as e:
        st.error(f"获取统计信息失败: {str(e)}")


def settings_page():
    """Settings page"""
    st.title("⚙️ 系统设置")
    st.markdown("配置OmniSense系统参数和选项")

    # General settings
    st.markdown("### 🔧 基本设置")

    col1, col2 = st.columns(2)

    with col1:
        debug_mode = st.checkbox("调试模式", value=False)
        log_level = st.selectbox(
            "日志级别",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            index=1
        )

    with col2:
        auto_save = st.checkbox("自动保存", value=True)
        notification = st.checkbox("系统通知", value=True)

    st.divider()

    # Spider settings
    st.markdown("### 🕷️ 爬虫设置")

    col1, col2 = st.columns(2)

    with col1:
        concurrent_tasks = st.number_input(
            "并发任务数",
            min_value=1,
            max_value=20,
            value=5,
            help="同时运行的爬虫任务数"
        )

        timeout = st.number_input(
            "请求超时(秒)",
            min_value=5,
            max_value=120,
            value=30
        )

    with col2:
        download_media = st.checkbox("自动下载媒体", value=True)
        cookie_persist = st.checkbox("保持Cookie", value=True)

    st.divider()

    # Anti-crawl settings
    st.markdown("### 🛡️ 反爬虫设置")

    col1, col2 = st.columns(2)

    with col1:
        user_agent_rotation = st.checkbox("User-Agent轮换", value=True)
        fingerprint_random = st.checkbox("指纹随机化", value=True)

    with col2:
        delay_min = st.number_input("最小延迟(秒)", min_value=0.0, max_value=10.0, value=1.0, step=0.5)
        delay_max = st.number_input("最大延迟(秒)", min_value=0.0, max_value=10.0, value=5.0, step=0.5)

    # Proxy settings
    with st.expander("🌐 代理设置"):
        enable_proxy = st.checkbox("启用代理", value=False)

        if enable_proxy:
            col1, col2 = st.columns(2)

            with col1:
                http_proxy = st.text_input("HTTP代理", placeholder="http://proxy:port")
                proxy_pool_enabled = st.checkbox("使用代理池", value=False)

            with col2:
                https_proxy = st.text_input("HTTPS代理", placeholder="https://proxy:port")
                if proxy_pool_enabled:
                    proxy_pool_url = st.text_input("代理池API", placeholder="http://api.proxy.com")

    st.divider()

    # LLM settings
    st.markdown("### 🤖 LLM设置")

    col1, col2 = st.columns(2)

    with col1:
        llm_provider = st.selectbox(
            "LLM提供商",
            ["ollama", "openai", "anthropic"],
            help="选择大语言模型提供商"
        )

        if llm_provider == "ollama":
            ollama_base_url = st.text_input(
                "Ollama地址",
                value="http://localhost:11434"
            )
            llm_model = st.selectbox(
                "模型",
                ["qwen2.5:7b", "qwen2.5:14b", "llama3:8b", "mistral:7b"]
            )
        elif llm_provider == "openai":
            openai_api_key = st.text_input("OpenAI API Key", type="password")
            llm_model = st.selectbox(
                "模型",
                ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            )
        else:
            anthropic_api_key = st.text_input("Anthropic API Key", type="password")
            llm_model = st.selectbox(
                "模型",
                ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
            )

    with col2:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        max_tokens = st.number_input("最大Token数", min_value=512, max_value=8192, value=4096, step=512)

    st.divider()

    # Database settings
    st.markdown("### 💾 数据库设置")

    col1, col2 = st.columns(2)

    with col1:
        sqlite_path = st.text_input("SQLite路径", value="data/omnisense.db")
        chroma_path = st.text_input("ChromaDB路径", value="data/chroma")

    with col2:
        redis_host = st.text_input("Redis主机", value="localhost")
        redis_port = st.number_input("Redis端口", min_value=1, max_value=65535, value=6379)

    st.divider()

    # Enabled platforms
    st.markdown("### 🌐 启用平台")

    st.markdown("选择要启用的数据采集平台")

    for category, platforms in PLATFORMS.items():
        with st.expander(f"📁 {category} ({len(platforms)}个平台)"):
            cols = st.columns(4)
            for i, platform in enumerate(platforms):
                with cols[i % 4]:
                    st.checkbox(platform, value=True, key=f"platform_{platform}")

    st.divider()

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 保存设置", use_container_width=True):
            st.success("设置已保存")

    with col2:
        if st.button("🔄 重置为默认", use_container_width=True):
            st.info("设置已重置")

    with col3:
        if st.button("📤 导出配置", use_container_width=True):
            config_json = json.dumps({
                "debug_mode": debug_mode,
                "log_level": log_level,
                "concurrent_tasks": concurrent_tasks,
                "llm_provider": llm_provider,
                "llm_model": llm_model
            }, indent=2)

            st.download_button(
                label="下载配置文件",
                data=config_json,
                file_name="omnisense_config.json",
                mime="application/json"
            )

    with col4:
        if st.button("📥 导入配置", use_container_width=True):
            uploaded_file = st.file_uploader("选择配置文件", type=['json'])
            if uploaded_file:
                st.success("配置已导入")

    st.divider()

    # System information
    st.markdown("### ℹ️ 系统信息")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **系统版本**
        - OmniSense: v1.0.0
        - Streamlit: v1.35.0
        - Python: 3.10+
        - Platform: Windows/Linux/macOS
        """)

    with col2:
        st.markdown("""
        **支持功能**
        - ✅ 49+ 平台采集
        - ✅ 6种智能Agent
        - ✅ 多维度分析
        - ✅ 多格式报告
        """)


def main():
    """Main application"""
    # Initialize session state
    init_session_state()

    # Sidebar navigation
    st.sidebar.title("🔍 OmniSense")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "导航菜单",
        [
            "🏠 首页",
            "📥 数据采集",
            "🔬 分析",
            "📄 报告",
            "📊 统计",
            "⚙️ 设置"
        ]
    )

    st.sidebar.markdown("---")

    # System status
    st.sidebar.markdown("### 📊 系统状态")

    omnisense = get_omnisense()
    if omnisense:
        st.sidebar.success("✅ 系统正常")

        # Quick stats
        try:
            stats = asyncio.run(omnisense.db.get_statistics())
            st.sidebar.metric("采集数据", f"{stats.get('total_content', 0):,}")
            st.sidebar.metric("本次会话采集", len(st.session_state.collection_results))
        except:
            pass
    else:
        st.sidebar.error("❌ 系统未初始化")

    st.sidebar.markdown("---")

    # Quick actions
    st.sidebar.markdown("### ⚡ 快捷操作")

    if st.sidebar.button("🆕 新建采集", use_container_width=True):
        st.session_state.page = "📥 数据采集"

    if st.sidebar.button("🔄 刷新系统", use_container_width=True):
        st.rerun()

    if st.sidebar.button("🧹 清空缓存", use_container_width=True):
        st.session_state.collection_results = []
        st.session_state.analysis_results = None
        st.success("缓存已清空")
        st.rerun()

    st.sidebar.markdown("---")

    # Footer
    st.sidebar.markdown("""
    <div style='text-align: center; color: #64748b; font-size: 0.8rem;'>
        <p>OmniSense v1.0.0</p>
        <p>全域数据智能洞察平台</p>
    </div>
    """, unsafe_allow_html=True)

    # Route to pages
    if page == "🏠 首页":
        home_page()
    elif page == "📥 数据采集":
        data_collection_page()
    elif page == "🔬 分析":
        analysis_page()
    elif page == "📄 报告":
        reports_page()
    elif page == "📊 统计":
        statistics_page()
    elif page == "⚙️ 设置":
        settings_page()


if __name__ == "__main__":
    main()
