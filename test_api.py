"""
Test script for OmniSense API
Run with: python test_api.py
"""

import requests
import json
import time
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin"


class OmniSenseAPIClient:
    """Client for testing OmniSense API"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.api_key = None

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get JWT token"""
        print(f"\n[TEST] Logging in as {username}...")

        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            print(f"✓ Login successful. Token: {self.token[:20]}...")
            return data
        else:
            print(f"✗ Login failed: {response.text}")
            return {}

    def create_api_key(self) -> Dict[str, Any]:
        """Create API key"""
        print("\n[TEST] Creating API key...")

        response = requests.post(
            f"{self.base_url}/api/v1/auth/apikey",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            data = response.json()
            self.api_key = data["data"]["api_key"]
            print(f"✓ API key created: {self.api_key[:20]}...")
            return data
        else:
            print(f"✗ API key creation failed: {response.text}")
            return {}

    def start_collection(self, platform: str, keyword: str, max_count: int = 10) -> Dict[str, Any]:
        """Start data collection"""
        print(f"\n[TEST] Starting collection - Platform: {platform}, Keyword: {keyword}...")

        response = requests.post(
            f"{self.base_url}/api/v1/collect",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "platform": platform,
                "keyword": keyword,
                "max_count": max_count
            }
        )

        if response.status_code == 202:
            data = response.json()
            task_id = data["data"]["task_id"]
            print(f"✓ Collection task started. Task ID: {task_id}")
            return data
        else:
            print(f"✗ Collection failed: {response.text}")
            return {}

    def get_task_status(self, task_id: str, endpoint: str = "collect") -> Dict[str, Any]:
        """Get task status"""
        response = requests.get(
            f"{self.base_url}/api/v1/{endpoint}/{task_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Failed to get task status: {response.text}")
            return {}

    def wait_for_task(self, task_id: str, endpoint: str = "collect", timeout: int = 300) -> Dict[str, Any]:
        """Wait for task to complete"""
        print(f"\n[TEST] Waiting for task {task_id} to complete...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id, endpoint)

            if status.get("status") == "success":
                print(f"✓ Task completed successfully")
                return status
            elif status.get("status") == "failure":
                print(f"✗ Task failed: {status.get('error')}")
                return status
            elif status.get("status") in ["pending", "progress"]:
                progress = status.get("progress", 0)
                print(f"  Progress: {progress}%")
                time.sleep(5)
            else:
                print(f"  Status: {status.get('status')}")
                time.sleep(5)

        print(f"✗ Task timeout after {timeout} seconds")
        return {}

    def start_analysis(self, data: Dict[str, Any], agents: list = None, analysis_types: list = None) -> Dict[str, Any]:
        """Start analysis"""
        print(f"\n[TEST] Starting analysis...")

        response = requests.post(
            f"{self.base_url}/api/v1/analyze",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "data": data,
                "agents": agents or ["analyst"],
                "analysis_types": analysis_types or ["sentiment", "clustering"]
            }
        )

        if response.status_code == 202:
            data = response.json()
            task_id = data["data"]["task_id"]
            print(f"✓ Analysis task started. Task ID: {task_id}")
            return data
        else:
            print(f"✗ Analysis failed: {response.text}")
            return {}

    def generate_report(self, analysis: Dict[str, Any], format: str = "pdf") -> Dict[str, Any]:
        """Generate report"""
        print(f"\n[TEST] Generating {format.upper()} report...")

        response = requests.post(
            f"{self.base_url}/api/v1/report",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "analysis": analysis,
                "format": format
            }
        )

        if response.status_code == 202:
            data = response.json()
            task_id = data["data"]["task_id"]
            print(f"✓ Report generation started. Task ID: {task_id}")
            return data
        else:
            print(f"✗ Report generation failed: {response.text}")
            return {}

    def list_platforms(self) -> Dict[str, Any]:
        """List all platforms"""
        print("\n[TEST] Listing platforms...")

        response = requests.get(
            f"{self.base_url}/api/v1/platforms",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            platforms = response.json()
            print(f"✓ Found {len(platforms)} platforms")
            for platform in platforms[:5]:  # Show first 5
                print(f"  - {platform['name']}: {platform['display_name']}")
            return platforms
        else:
            print(f"✗ Failed to list platforms: {response.text}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        print("\n[TEST] Getting system statistics...")

        response = requests.get(
            f"{self.base_url}/api/v1/stats",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Statistics retrieved:")
            print(f"  - Collections: {stats['total_collections']}")
            print(f"  - Analyses: {stats['total_analyses']}")
            print(f"  - Active tasks: {stats['active_tasks']}")
            return stats
        else:
            print(f"✗ Failed to get stats: {response.text}")
            return {}

    def test_api_key_auth(self) -> bool:
        """Test API key authentication"""
        print("\n[TEST] Testing API key authentication...")

        response = requests.get(
            f"{self.base_url}/api/v1/stats",
            headers={"X-API-Key": self.api_key}
        )

        if response.status_code == 200:
            print("✓ API key authentication successful")
            return True
        else:
            print(f"✗ API key authentication failed: {response.text}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        print("\n[TEST] Checking API health...")

        response = requests.get(f"{self.base_url}/health")

        if response.status_code == 200:
            health = response.json()
            print(f"✓ API is healthy")
            print(f"  - Redis: {health['redis']}")
            print(f"  - Celery: {health['celery']}")
            return health
        else:
            print(f"✗ Health check failed: {response.text}")
            return {}


def run_comprehensive_test():
    """Run comprehensive API test"""
    print("=" * 80)
    print("OmniSense API Comprehensive Test")
    print("=" * 80)

    client = OmniSenseAPIClient(BASE_URL)

    # 1. Health check
    client.health_check()

    # 2. Login
    client.login(USERNAME, PASSWORD)

    # 3. Create API key
    client.create_api_key()

    # 4. Test API key authentication
    if client.api_key:
        client.test_api_key_auth()

    # 5. List platforms
    client.list_platforms()

    # 6. Get statistics
    client.get_stats()

    # 7. Start collection (comment out if you want to skip)
    # collection_result = client.start_collection(
    #     platform="douyin",
    #     keyword="AI编程",
    #     max_count=10
    # )
    # if collection_result.get("data", {}).get("task_id"):
    #     task_id = collection_result["data"]["task_id"]
    #     result = client.wait_for_task(task_id, "collect", timeout=60)

    # 8. Start analysis (with sample data)
    sample_data = [
        {"title": "AI编程工具", "description": "很好用的AI编程工具", "stats": {"likes": 100}},
        {"title": "Python教程", "description": "Python编程入门教程", "stats": {"likes": 80}},
    ]

    analysis_result = client.start_analysis(
        data=sample_data,
        agents=["analyst"],
        analysis_types=["sentiment"]
    )

    if analysis_result.get("data", {}).get("task_id"):
        task_id = analysis_result["data"]["task_id"]
        result = client.wait_for_task(task_id, "analyze", timeout=60)

        # 9. Generate report if analysis completed
        if result.get("status") == "success" and result.get("result"):
            report_result = client.generate_report(
                analysis=result["result"],
                format="html"
            )

            if report_result.get("data", {}).get("task_id"):
                task_id = report_result["data"]["task_id"]
                client.wait_for_task(task_id, "report", timeout=60)

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)


def run_quick_test():
    """Run quick API test (no async tasks)"""
    print("=" * 80)
    print("OmniSense API Quick Test")
    print("=" * 80)

    client = OmniSenseAPIClient(BASE_URL)

    # Basic tests
    client.health_check()
    client.login(USERNAME, PASSWORD)
    client.list_platforms()
    client.get_stats()

    print("\n" + "=" * 80)
    print("Quick test completed!")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        run_quick_test()
    else:
        run_comprehensive_test()
