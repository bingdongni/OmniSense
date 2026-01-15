"""
Cookie & API 混合数据采集示例

展示如何在OmniSense中使用三种数据采集方式:
1. 纯爬虫模式 (Scraping)
2. Cookie增强爬虫模式 (Cookie + Scraping)
3. 官方API模式 (Official API)
4. 混合模式 (Hybrid: API + Scraping fallback)

Author: bingdongni
Version: 1.0.0
"""

import asyncio
from pathlib import Path
from omnisense import OmniSense
from omnisense.auth import get_cookie_manager, get_api_manager
from omnisense.auth import APICredential, AuthType, RateLimitInfo
from datetime import datetime, timedelta

# 初始化OmniSense
omni = OmniSense()


async def example_1_pure_scraping():
    """
    示例1: 纯爬虫模式

    不使用Cookie和API，直接爬取公开数据
    适用于: 不需要登录的平台或公开内容
    """
    print("=" * 80)
    print("示例1: 纯爬虫模式 - 抓取公开数据")
    print("=" * 80)

    # 采集arXiv公开数据 (无需登录)
    result = await omni.collect_async(
        platform="arxiv",
        keyword="artificial intelligence",
        max_count=10,
        mode="scraping"  # 明确指定爬虫模式
    )

    print(f"✓ 采集到 {len(result)} 条arXiv论文数据")
    if result:
        print(f"  示例: {result[0].get('title', 'N/A')}")


async def example_2_cookie_enhanced():
    """
    示例2: Cookie增强爬虫模式

    使用用户提供的Cookie访问需要登录的内容
    适用于: 需要登录但没有官方API的平台
    """
    print("\n" + "=" * 80)
    print("示例2: Cookie增强爬虫模式 - 使用Cookie访问私密内容")
    print("=" * 80)

    cookie_manager = get_cookie_manager()

    # 方式1: 从浏览器导入Cookie
    print("\n方式1: 从Chrome浏览器导入Cookie")
    success = cookie_manager.import_from_browser_db(
        platform="xiaohongshu",
        browser="chrome",  # 或 "firefox", "edge"
        domain="xiaohongshu.com",
        user_id="user_001"
    )

    if success:
        print("✓ 成功从Chrome导入小红书Cookie")
    else:
        print("! Chrome导入失败，尝试手动导入")

    # 方式2: 从JSON文件导入Cookie
    print("\n方式2: 从JSON文件导入Cookie")
    # cookies.json 示例:
    # [
    #     {
    #         "name": "sessionid",
    #         "value": "your_session_id_here",
    #         "domain": ".xiaohongshu.com",
    #         "path": "/",
    #         "secure": true,
    #         "httpOnly": true
    #     }
    # ]

    # 如果有cookies.json文件
    if Path("data/cookies/xiaohongshu_cookies.json").exists():
        cookie_manager.import_from_json(
            platform="xiaohongshu",
            json_file="data/cookies/xiaohongshu_cookies.json",
            user_id="user_002"
        )
        print("✓ 成功从JSON文件导入Cookie")

    # 方式3: 手动提供Cookie字典
    print("\n方式3: 手动提供Cookie")
    cookies = {
        "sessionid": "your_session_id_here",
        "csrf_token": "your_csrf_token_here",
        "web_session": "your_web_session_here"
    }

    cookie_manager.import_from_dict(
        platform="xiaohongshu",
        cookies_dict=cookies,
        domain=".xiaohongshu.com",
        user_id="user_003"
    )
    print("✓ 成功导入手动Cookie")

    # 使用Cookie进行数据采集
    print("\n使用Cookie采集小红书数据...")
    result = await omni.collect_async(
        platform="xiaohongshu",
        keyword="护肤",
        max_count=20,
        use_cookie=True,  # 启用Cookie
        user_id="user_001"  # 指定使用哪个用户的Cookie
    )

    print(f"✓ 使用Cookie采集到 {len(result)} 条小红书数据")

    # 查看Cookie统计
    print("\nCookie池统计:")
    stats = cookie_manager.get_statistics()
    for platform, info in stats.items():
        print(f"  {platform}: {info['valid_sets']}/{info['total_sets']} 有效Cookie集合")


async def example_3_official_api():
    """
    示例3: 官方API模式

    使用平台官方API进行数据采集
    适用于: 有官方API的平台(GitHub, Twitter, YouTube等)
    """
    print("\n" + "=" * 80)
    print("示例3: 官方API模式 - 使用GitHub API")
    print("=" * 80)

    api_manager = get_api_manager()

    # 添加GitHub API凭证
    github_credential = APICredential(
        platform="github",
        auth_type=AuthType.BEARER_TOKEN,
        access_token="your_github_personal_access_token",  # 从 https://github.com/settings/tokens 获取
        user_id="github_user_001",
        account_name="my_github_account",
        metadata={
            "scopes": ["repo", "user", "read:org"],
            "created_at": datetime.now().isoformat()
        }
    )

    api_manager.add_credential(github_credential)
    print("✓ 添加GitHub API凭证")

    # 使用API采集数据
    print("\n使用GitHub API搜索仓库...")
    result = await omni.collect_async(
        platform="github",
        keyword="machine learning",
        max_count=30,
        mode="api",  # 明确指定API模式
        filters={
            "language": "python",
            "stars": ">100"
        }
    )

    print(f"✓ 使用API采集到 {len(result)} 个GitHub仓库")
    if result:
        print(f"  示例: {result[0].get('full_name', 'N/A')} - {result[0].get('stars', 0)} stars")


async def example_4_hybrid_mode():
    """
    示例4: 混合模式

    优先使用API，失败时回退到爬虫
    这是推荐的生产环境配置
    """
    print("\n" + "=" * 80)
    print("示例4: 混合模式 - API优先，爬虫回退")
    print("=" * 80)

    # 配置混合模式
    omni.config.platform.collection_mode["douyin"] = "hybrid"
    omni.config.api.prefer_api = True
    omni.config.api.fallback_to_scraping = True

    print("配置: API优先，失败时自动切换到爬虫")

    # 采集抖音数据
    result = await omni.collect_async(
        platform="douyin",
        keyword="美食",
        max_count=50,
        mode="hybrid"  # 混合模式
    )

    print(f"✓ 采集到 {len(result)} 条抖音数据")
    print(f"  使用方式: {result[0].get('_collection_method', 'unknown') if result else 'N/A'}")


async def example_5_cookie_rotation():
    """
    示例5: Cookie池轮换

    使用多个Cookie轮换，避免单个账号被封
    """
    print("\n" + "=" * 80)
    print("示例5: Cookie池轮换 - 多账号轮换避免封禁")
    print("=" * 80)

    cookie_manager = get_cookie_manager()

    # 添加多个账号的Cookie
    for i in range(3):
        cookies = {
            "sessionid": f"session_account_{i+1}",
            "csrf_token": f"csrf_account_{i+1}"
        }

        cookie_manager.import_from_dict(
            platform="weibo",
            cookies_dict=cookies,
            domain=".weibo.com",
            user_id=f"weibo_user_{i+1}"
        )

    print(f"✓ 添加了 3 个微博账号Cookie")

    # 多次采集，自动轮换Cookie
    for round_num in range(5):
        result = await omni.collect_async(
            platform="weibo",
            keyword="热点新闻",
            max_count=10,
            use_cookie=True,
            rotate_cookie=True  # 启用Cookie轮换
        )

        print(f"  第{round_num+1}轮采集: {len(result)} 条数据")


async def example_6_api_rate_limiting():
    """
    示例6: API速率限制管理

    自动处理API速率限制，避免超限
    """
    print("\n" + "=" * 80)
    print("示例6: API速率限制管理")
    print("=" * 80)

    api_manager = get_api_manager()

    # 添加带速率限制的Twitter API凭证
    twitter_credential = APICredential(
        platform="twitter",
        auth_type=AuthType.OAUTH2,
        access_token="your_twitter_bearer_token",
        user_id="twitter_user_001"
    )

    # 设置速率限制: 15请求/15分钟 (Twitter标准限制)
    rate_limit = RateLimitInfo(
        max_requests=15,
        time_window=900,  # 15分钟 = 900秒
        remaining=15,
        reset_at=datetime.now() + timedelta(minutes=15)
    )

    api_manager.add_credential(twitter_credential)
    print("✓ 添加Twitter API凭证，速率限制: 15请求/15分钟")

    # 进行多次请求，自动处理速率限制
    print("\n发起20个请求 (超出限制，会自动等待)...")
    for i in range(20):
        try:
            result = await omni.collect_async(
                platform="twitter",
                keyword=f"topic_{i}",
                max_count=1,
                mode="api"
            )
            print(f"  请求 {i+1}: {'成功' if result else '失败'}")
        except Exception as e:
            print(f"  请求 {i+1}: 等待速率限制重置...")


async def example_7_cookie_validation():
    """
    示例7: Cookie有效性验证

    自动验证Cookie是否仍然有效
    """
    print("\n" + "=" * 80)
    print("示例7: Cookie有效性验证")
    print("=" * 80)

    cookie_manager = get_cookie_manager()

    # 验证抖音Cookie
    print("验证抖音Cookie...")
    results = await cookie_manager.validate_cookies(
        platform="douyin",
        validation_url="https://www.douyin.com/",
        success_indicator="推荐"  # 登录成功后页面会包含此文本
    )

    for cookie_set, is_valid in results:
        status = "有效✓" if is_valid else "无效✗"
        print(f"  账号 {cookie_set.account_name}: {status}")


async def example_8_data_collection_comparison():
    """
    示例8: 三种模式对比

    对比三种模式的速度、数据量和成本
    """
    print("\n" + "=" * 80)
    print("示例8: 数据采集模式对比")
    print("=" * 80)

    import time

    test_platforms = [
        ("github", "api"),
        ("github", "scraping"),
        ("github", "hybrid")
    ]

    for platform, mode in test_platforms:
        start_time = time.time()

        result = await omni.collect_async(
            platform=platform,
            keyword="python",
            max_count=10,
            mode=mode
        )

        elapsed = time.time() - start_time
        print(f"\n{mode.upper()}模式:")
        print(f"  采集数量: {len(result)}")
        print(f"  耗时: {elapsed:.2f}秒")
        print(f"  平均速度: {len(result)/elapsed:.2f}条/秒")


async def main():
    """运行所有示例"""
    print("=" * 80)
    print("OmniSense Cookie & API 混合数据采集示例")
    print("=" * 80)

    examples = [
        ("纯爬虫模式", example_1_pure_scraping),
        ("Cookie增强模式", example_2_cookie_enhanced),
        ("官方API模式", example_3_official_api),
        ("混合模式", example_4_hybrid_mode),
        ("Cookie池轮换", example_5_cookie_rotation),
        ("API速率限制", example_6_api_rate_limiting),
        ("Cookie验证", example_7_cookie_validation),
        ("模式对比", example_8_data_collection_comparison)
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n! 示例 '{name}' 执行出错: {e}")

    print("\n" + "=" * 80)
    print("所有示例执行完成！")
    print("=" * 80)

    # 显示最终统计
    cookie_manager = get_cookie_manager()
    api_manager = get_api_manager()

    print("\n最终统计:")
    print(f"  Cookie池: {cookie_manager.get_statistics()}")
    print(f"  API凭证: {api_manager.get_statistics()}")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
