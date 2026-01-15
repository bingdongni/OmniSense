"""
Agent Manager for Multi-Agent Orchestration
负责协调和管理多个智能体的协作
"""

import asyncio
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict

from loguru import logger
from pydantic import BaseModel, Field

from .base import BaseAgent, AgentRole, AgentState, AgentResponse, AgentConfig


class TaskPriority(str):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentTask(BaseModel):
    """Agent task definition"""
    task_id: str
    agent_role: AgentRole
    priority: TaskPriority = TaskPriority.MEDIUM
    parameters: Dict[str, Any]
    context: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)  # Task IDs
    assigned_agent: Optional[str] = None
    status: str = "pending"
    result: Optional[AgentResponse] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AgentManager:
    """
    Multi-agent orchestration manager

    Features:
    - Agent lifecycle management
    - Task distribution and scheduling
    - Agent collaboration coordination
    - Resource management
    - Result aggregation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.task_queue: List[AgentTask] = []
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()

        # Performance tracking
        self.metrics = defaultdict(lambda: {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_time": 0.0,
            "avg_confidence": 0.0
        })

        # Forum integration
        self.forum_engine: Optional[Any] = None  # ForumEngine instance

        logger.info("Initialized AgentManager")

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the manager"""
        if agent.name in self.agents:
            logger.warning(f"Agent {agent.name} already registered, updating...")

        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.role.value})")

    def unregister_agent(self, agent_name: str):
        """Unregister an agent"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")

    def get_agent_by_role(self, role: AgentRole) -> Optional[BaseAgent]:
        """Get first available agent by role"""
        for agent in self.agents.values():
            if agent.role == role and agent.state == AgentState.IDLE:
                return agent
        return None

    def get_agents_by_role(self, role: AgentRole) -> List[BaseAgent]:
        """Get all agents with specific role"""
        return [agent for agent in self.agents.values() if agent.role == role]

    async def submit_task(
        self,
        agent_role: AgentRole,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Submit a task to the manager

        Args:
            agent_role: Required agent role
            parameters: Task parameters
            priority: Task priority
            context: Additional context
            dependencies: List of task IDs that must complete first

        Returns:
            Task ID
        """
        task_id = f"task_{len(self.tasks)}_{int(datetime.now().timestamp())}"

        task = AgentTask(
            task_id=task_id,
            agent_role=agent_role,
            priority=priority,
            parameters=parameters,
            context=context or {},
            dependencies=dependencies or []
        )

        self.tasks[task_id] = task
        self.task_queue.append(task)

        # Sort queue by priority
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3
        }
        self.task_queue.sort(key=lambda t: priority_order.get(t.priority, 2))

        logger.info(f"Submitted task {task_id} for {agent_role.value}")
        return task_id

    async def _execute_task(self, task: AgentTask) -> AgentResponse:
        """Execute a single task"""
        # Find available agent
        agent = self.get_agent_by_role(task.agent_role)
        if not agent:
            raise ValueError(f"No available agent for role {task.agent_role.value}")

        task.assigned_agent = agent.name
        task.status = "running"
        task.started_at = datetime.now()

        try:
            # Execute task
            result = await agent.process(task.parameters, task.context)
            task.result = result
            task.status = "completed" if result.success else "failed"
            task.completed_at = datetime.now()

            # Update metrics
            execution_time = (task.completed_at - task.started_at).total_seconds()
            metrics = self.metrics[agent.name]
            metrics["total_tasks"] += 1

            if result.success:
                metrics["successful_tasks"] += 1
                self.completed_tasks.add(task.task_id)
            else:
                metrics["failed_tasks"] += 1
                self.failed_tasks.add(task.task_id)

            metrics["total_time"] += execution_time
            metrics["avg_confidence"] = (
                (metrics["avg_confidence"] * (metrics["total_tasks"] - 1) + result.confidence)
                / metrics["total_tasks"]
            )

            logger.info(
                f"Task {task.task_id} completed by {agent.name} "
                f"in {execution_time:.2f}s (success={result.success})"
            )

            return result

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            task.status = "failed"
            task.completed_at = datetime.now()
            self.failed_tasks.add(task.task_id)

            return AgentResponse(
                agent_name=agent.name,
                agent_role=agent.role,
                success=False,
                error=str(e)
            )

    async def _wait_for_dependencies(self, task: AgentTask, timeout: int = 300):
        """Wait for task dependencies to complete"""
        if not task.dependencies:
            return True

        start_time = datetime.now()

        while True:
            # Check if all dependencies are completed
            all_completed = all(
                dep_id in self.completed_tasks
                for dep_id in task.dependencies
            )

            if all_completed:
                return True

            # Check for failed dependencies
            any_failed = any(
                dep_id in self.failed_tasks
                for dep_id in task.dependencies
            )

            if any_failed:
                logger.error(f"Task {task.task_id} has failed dependencies")
                return False

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                logger.error(f"Task {task.task_id} dependency timeout")
                return False

            await asyncio.sleep(1)

    async def run_task(self, task_id: str) -> AgentResponse:
        """Run a specific task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        if task.task_id in self.running_tasks:
            raise ValueError(f"Task {task_id} is already running")

        # Wait for dependencies
        deps_ready = await self._wait_for_dependencies(task)
        if not deps_ready:
            return AgentResponse(
                agent_name="manager",
                agent_role=AgentRole.MANAGER,
                success=False,
                error="Dependencies not satisfied"
            )

        self.running_tasks.add(task.task_id)

        try:
            result = await self._execute_task(task)
            return result
        finally:
            self.running_tasks.discard(task.task_id)

    async def run_all_tasks(self, max_concurrent: int = 5) -> List[AgentResponse]:
        """
        Run all pending tasks with concurrency control

        Args:
            max_concurrent: Maximum concurrent tasks

        Returns:
            List of agent responses
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(task: AgentTask):
            async with semaphore:
                return await self.run_task(task.task_id)

        # Create tasks for all pending items
        pending_tasks = [
            task for task in self.task_queue
            if task.status == "pending"
        ]

        if not pending_tasks:
            logger.info("No pending tasks to run")
            return results

        logger.info(f"Running {len(pending_tasks)} tasks with max_concurrent={max_concurrent}")

        # Run tasks concurrently
        task_coroutines = [run_with_semaphore(task) for task in pending_tasks]
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)

        # Handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                results[i] = AgentResponse(
                    agent_name="manager",
                    agent_role=AgentRole.MANAGER,
                    success=False,
                    error=str(result)
                )

        return results

    async def orchestrate_workflow(
        self,
        workflow: List[Dict[str, Any]]
    ) -> Dict[str, AgentResponse]:
        """
        Orchestrate a complex workflow with multiple agents

        Args:
            workflow: List of workflow steps, each with:
                - role: AgentRole
                - parameters: Task parameters
                - depends_on: List of step indices

        Returns:
            Dictionary mapping step index to response
        """
        task_ids = {}
        results = {}

        for i, step in enumerate(workflow):
            role = step["role"]
            parameters = step["parameters"]
            depends_on = step.get("depends_on", [])

            # Get dependency task IDs
            dependencies = [task_ids[dep] for dep in depends_on if dep in task_ids]

            # Submit task
            task_id = await self.submit_task(
                agent_role=role,
                parameters=parameters,
                priority=step.get("priority", TaskPriority.MEDIUM),
                dependencies=dependencies
            )

            task_ids[i] = task_id

        # Run all tasks
        responses = await self.run_all_tasks()

        # Map responses to step indices
        for i, task_id in task_ids.items():
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.result:
                    results[i] = task.result

        return results

    async def collaborate_agents(
        self,
        agents: List[BaseAgent],
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Facilitate collaboration between multiple agents

        Args:
            agents: List of agents to collaborate
            task: Task parameters
            context: Shared context

        Returns:
            Combined agent response
        """
        if len(agents) < 2:
            raise ValueError("At least 2 agents required for collaboration")

        logger.info(f"Collaborating {len(agents)} agents: {[a.name for a in agents]}")

        # Execute all agents in parallel
        responses = await asyncio.gather(*[
            agent.process(task, context)
            for agent in agents
        ])

        # Aggregate results
        combined_data = {
            agent.name: response.data
            for agent, response in zip(agents, responses)
        }

        all_reasoning = []
        for response in responses:
            all_reasoning.extend(response.reasoning)

        avg_confidence = sum(r.confidence for r in responses) / len(responses)
        all_success = all(r.success for r in responses)

        # Synthesize with primary agent
        primary_agent = agents[0]
        synthesis_prompt = f"""
Synthesize responses from {len(agents)} agents:

{chr(10).join(f"{agent.name}: {response.message}" for agent, response in zip(agents, responses))}

Provide a unified comprehensive response:
"""

        try:
            synthesis = await primary_agent.llm.ainvoke(synthesis_prompt)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            synthesis = "Synthesis failed"

        return AgentResponse(
            agent_name="collaborative_team",
            agent_role=AgentRole.MANAGER,
            success=all_success,
            data=combined_data,
            message=synthesis,
            reasoning=all_reasoning,
            confidence=avg_confidence,
            metadata={
                "collaboration": True,
                "agents": [a.name for a in agents],
                "individual_responses": len(responses)
            }
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "agents": {
                name: {
                    "status": agent.get_status(),
                    "metrics": self.metrics[name]
                }
                for name, agent in self.agents.items()
            },
            "tasks": {
                "total": len(self.tasks),
                "pending": len([t for t in self.tasks.values() if t.status == "pending"]),
                "running": len(self.running_tasks),
                "completed": len(self.completed_tasks),
                "failed": len(self.failed_tasks)
            }
        }

    def initialize_forum(self, llm, forum_config: Optional[Dict[str, Any]] = None):
        """
        Initialize ForumEngine for agent collaboration

        Args:
            llm: LLM instance for moderator
            forum_config: Forum configuration
        """
        from omnisense.forum import ForumEngine

        self.forum_engine = ForumEngine(llm=llm, config=forum_config)

        # Register all existing agents with forum
        for agent_id, agent in self.agents.items():
            queue = self.forum_engine.register_agent(agent_id, agent)
            # Note: Agents will join forum when session starts

        logger.info("ForumEngine initialized and agents registered")

    async def start_forum_session(
        self,
        topic: str,
        agent_ids: Optional[List[str]] = None,
        max_rounds: int = 10,
        timeout_seconds: int = 300,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a forum collaboration session

        Args:
            topic: Discussion topic
            agent_ids: List of agent IDs to participate (None = all agents)
            max_rounds: Maximum discussion rounds
            timeout_seconds: Session timeout
            initial_context: Initial context for discussion

        Returns:
            Session ID
        """
        if not self.forum_engine:
            raise RuntimeError("ForumEngine not initialized. Call initialize_forum() first.")

        # Default to all agents if none specified
        if agent_ids is None:
            agent_ids = list(self.agents.keys())

        # Validate agents exist
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

        # Start forum session
        session_id = await self.forum_engine.start_session(
            topic=topic,
            agent_ids=agent_ids,
            max_rounds=max_rounds,
            timeout_seconds=timeout_seconds,
            initial_context=initial_context
        )

        # Have agents join the forum
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            queue = self.forum_engine.message_bus.register_agent(agent_id)
            await agent.join_forum(queue)

        logger.info(f"Forum session {session_id} started with {len(agent_ids)} agents")

        return session_id

    async def stop_forum_session(self, session_id: str):
        """
        Stop a forum session

        Args:
            session_id: Session ID to stop
        """
        if not self.forum_engine:
            raise RuntimeError("ForumEngine not initialized")

        # Get session to find participating agents
        session = self.forum_engine.get_session(session_id)
        if session:
            # Have agents leave forum
            for agent_id in session.agents:
                if agent_id in self.agents:
                    await self.agents[agent_id].leave_forum()

        # Stop the session
        await self.forum_engine.stop_session(session_id)

        logger.info(f"Forum session {session_id} stopped")

    def get_forum_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get forum session information

        Args:
            session_id: Session ID

        Returns:
            Session information dictionary
        """
        if not self.forum_engine:
            return None

        session = self.forum_engine.get_session(session_id)
        return session.to_dict() if session else None

    def list_forum_sessions(self) -> List[Dict[str, Any]]:
        """
        List all forum sessions

        Returns:
            List of session information
        """
        if not self.forum_engine:
            return []

        return self.forum_engine.list_sessions()

    def get_forum_statistics(self) -> Dict[str, Any]:
        """
        Get forum engine statistics

        Returns:
            Forum statistics
        """
        if not self.forum_engine:
            return {}

        return self.forum_engine.get_statistics()

    def reset(self):
        """Reset all agents and clear tasks"""
        for agent in self.agents.values():
            agent.reset()

        self.tasks.clear()
        self.task_queue.clear()
        self.running_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self.metrics.clear()

        logger.info("Reset AgentManager")
