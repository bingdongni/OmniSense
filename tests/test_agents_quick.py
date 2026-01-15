"""
Quick Test Script for OmniSense Multi-Agent System
快速测试脚本
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_imports():
    """Test that all agents can be imported"""
    print("Testing imports...")

    try:
        from omnisense.agents import (
            BaseAgent,
            AgentConfig,
            AgentResponse,
            AgentManager,
            ScoutAgent,
            AnalystAgent,
            EcommerceAgent,
            AcademicAgent,
            CreatorAgent,
            ReportAgent,
            AgentRole,
            AgentState
        )
        print("✓ All imports successful\n")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}\n")
        return False


async def test_agent_creation():
    """Test that agents can be created"""
    print("Testing agent creation...")

    try:
        from omnisense.agents import (
            ScoutAgent,
            AnalystAgent,
            EcommerceAgent,
            AcademicAgent,
            CreatorAgent,
            ReportAgent,
            AgentManager
        )

        # Create agents
        scout = ScoutAgent()
        print(f"✓ ScoutAgent created: {scout.name}")

        analyst = AnalystAgent()
        print(f"✓ AnalystAgent created: {analyst.name}")

        ecommerce = EcommerceAgent()
        print(f"✓ EcommerceAgent created: {ecommerce.name}")

        academic = AcademicAgent()
        print(f"✓ AcademicAgent created: {academic.name}")

        creator = CreatorAgent()
        print(f"✓ CreatorAgent created: {creator.name}")

        report = ReportAgent()
        print(f"✓ ReportAgent created: {report.name}")

        manager = AgentManager()
        print(f"✓ AgentManager created")

        print("\n")
        return True
    except Exception as e:
        print(f"✗ Agent creation failed: {e}\n")
        return False


async def test_agent_status():
    """Test agent status methods"""
    print("Testing agent status...")

    try:
        from omnisense.agents import ScoutAgent

        scout = ScoutAgent()
        status = scout.get_status()

        print(f"✓ Agent status retrieved:")
        print(f"  - Name: {status['name']}")
        print(f"  - Role: {status['role']}")
        print(f"  - State: {status['state']}")
        print(f"  - Memory size: {status['memory_size']}")

        print("\n")
        return True
    except Exception as e:
        print(f"✗ Status check failed: {e}\n")
        return False


async def test_manager_registration():
    """Test agent registration with manager"""
    print("Testing agent registration...")

    try:
        from omnisense.agents import (
            AgentManager,
            ScoutAgent,
            AnalystAgent,
            AgentRole
        )

        manager = AgentManager()

        scout = ScoutAgent()
        manager.register_agent(scout)
        print(f"✓ Registered ScoutAgent")

        analyst = AnalystAgent()
        manager.register_agent(analyst)
        print(f"✓ Registered AnalystAgent")

        # Get agent by role
        retrieved_scout = manager.get_agent_by_role(AgentRole.SCOUT)
        print(f"✓ Retrieved agent by role: {retrieved_scout.name}")

        # Get metrics
        metrics = manager.get_metrics()
        print(f"✓ Manager metrics retrieved:")
        print(f"  - Total agents: {len(metrics['agents'])}")
        print(f"  - Total tasks: {metrics['tasks']['total']}")

        print("\n")
        return True
    except Exception as e:
        print(f"✗ Registration failed: {e}\n")
        return False


async def test_chain_setup():
    """Test that LangChain chains are set up"""
    print("Testing LangChain chain setup...")

    try:
        from omnisense.agents import ScoutAgent

        scout = ScoutAgent()

        # Check chains
        print(f"✓ ScoutAgent chains: {list(scout.chains.keys())}")

        print("\n")
        return True
    except Exception as e:
        print(f"✗ Chain setup check failed: {e}\n")
        return False


async def test_response_model():
    """Test AgentResponse model"""
    print("Testing AgentResponse model...")

    try:
        from omnisense.agents import AgentResponse, AgentRole
        from datetime import datetime

        response = AgentResponse(
            agent_name="TestAgent",
            agent_role=AgentRole.SCOUT,
            success=True,
            data={"test": "data"},
            message="Test message",
            reasoning=["step 1", "step 2"],
            confidence=0.85
        )

        print(f"✓ AgentResponse created:")
        print(f"  - Agent: {response.agent_name}")
        print(f"  - Role: {response.agent_role}")
        print(f"  - Success: {response.success}")
        print(f"  - Confidence: {response.confidence}")
        print(f"  - Timestamp: {response.timestamp}")

        print("\n")
        return True
    except Exception as e:
        print(f"✗ Response model test failed: {e}\n")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("OmniSense Multi-Agent System - Quick Test")
    print("=" * 60 + "\n")

    tests = [
        ("Imports", test_imports),
        ("Agent Creation", test_agent_creation),
        ("Agent Status", test_agent_status),
        ("Manager Registration", test_manager_registration),
        ("Chain Setup", test_chain_setup),
        ("Response Model", test_response_model),
    ]

    results = []
    for test_name, test_func in tests:
        result = await test_func()
        results.append((test_name, result))

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Multi-agent system is ready.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
