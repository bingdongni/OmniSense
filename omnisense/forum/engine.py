#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forum Engine

Agent协作论坛引擎，协调多个Agent进行讨论和决策
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from loguru import logger

from .message_bus import MessageBus, Message, MessageType
from .monitor import ForumMonitor
from .moderator import LLMModerator


class ForumSession:
    """论坛会话"""

    def __init__(
        self,
        session_id: str,
        topic: str,
        agents: List[str],
        max_rounds: int = 10,
        timeout_seconds: int = 300
    ):
        """
        初始化会话

        Args:
            session_id: 会话ID
            topic: 讨论主题
            agents: 参与Agent列表
            max_rounds: 最大轮次
            timeout_seconds: 超时时间（秒）
        """
        self.session_id = session_id
        self.topic = topic
        self.agents = agents
        self.max_rounds = max_rounds
        self.timeout_seconds = timeout_seconds
        self.current_round = 0
        self.start_time = datetime.now()
        self.status = "initialized"  # initialized, running, completed, timeout, error
        self.result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "agents": self.agents,
            "max_rounds": self.max_rounds,
            "timeout_seconds": self.timeout_seconds,
            "current_round": self.current_round,
            "start_time": self.start_time.isoformat(),
            "status": self.status,
            "result": self.result
        }


class ForumEngine:
    """论坛引擎"""

    def __init__(
        self,
        llm,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化论坛引擎

        Args:
            llm: LLM实例
            config: 配置
        """
        self.llm = llm
        self.config = config or {}

        # 初始化核心组件
        self.message_bus = MessageBus()
        self.monitor = ForumMonitor(self.message_bus)
        self.moderator = LLMModerator(
            llm=llm,
            message_bus=self.message_bus,
            monitor=self.monitor,
            config=self.config.get('moderator', {})
        )

        # 会话管理
        self.sessions: Dict[str, ForumSession] = {}
        self.active_agents: Dict[str, Any] = {}  # agent_id -> agent instance

        logger.info("ForumEngine initialized")

    def register_agent(self, agent_id: str, agent: Any):
        """
        注册Agent

        Args:
            agent_id: Agent ID
            agent: Agent实例
        """
        self.active_agents[agent_id] = agent
        queue = self.message_bus.register_agent(agent_id)
        logger.info(f"Agent registered: {agent_id}")
        return queue

    def unregister_agent(self, agent_id: str):
        """
        注销Agent

        Args:
            agent_id: Agent ID
        """
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
        self.message_bus.unregister_agent(agent_id)
        logger.info(f"Agent unregistered: {agent_id}")

    async def start_session(
        self,
        topic: str,
        agent_ids: List[str],
        max_rounds: int = 10,
        timeout_seconds: int = 300,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        启动论坛会话

        Args:
            topic: 讨论主题
            agent_ids: 参与Agent ID列表
            max_rounds: 最大轮次
            timeout_seconds: 超时时间
            initial_context: 初始上下文

        Returns:
            会话ID
        """
        # 生成会话ID
        session_id = f"forum_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.sessions)}"

        # 验证Agent
        for agent_id in agent_ids:
            if agent_id not in self.active_agents:
                raise ValueError(f"Agent {agent_id} not registered")

        # 创建会话
        session = ForumSession(
            session_id=session_id,
            topic=topic,
            agents=agent_ids,
            max_rounds=max_rounds,
            timeout_seconds=timeout_seconds
        )
        self.sessions[session_id] = session

        logger.info(f"Forum session started: {session_id}, topic: {topic}")

        # 发送会话启动消息
        start_message = Message(
            type=MessageType.SESSION_START,
            sender="forum_engine",
            content=f"论坛会话开始: {topic}",
            data={
                "session_id": session_id,
                "topic": topic,
                "agents": agent_ids,
                "initial_context": initial_context or {}
            }
        )
        await self.message_bus.publish(start_message)

        # 启动会话异步任务
        asyncio.create_task(self._run_session(session_id))

        return session_id

    async def _run_session(self, session_id: str):
        """
        运行会话

        Args:
            session_id: 会话ID
        """
        session = self.sessions[session_id]
        session.status = "running"

        try:
            # 启动监控
            await self.monitor.start()

            # 主讨论循环
            while session.current_round < session.max_rounds:
                session.current_round += 1
                logger.info(f"Session {session_id} - Round {session.current_round}/{session.max_rounds}")

                # 发送轮次开始消息
                round_message = Message(
                    type=MessageType.ROUND_START,
                    sender="forum_engine",
                    content=f"第 {session.current_round} 轮讨论开始",
                    data={
                        "session_id": session_id,
                        "round": session.current_round
                    }
                )
                await self.message_bus.publish(round_message)

                # 等待Agent响应
                await asyncio.sleep(2)  # 给Agent时间处理消息

                # 检查是否超时
                elapsed = (datetime.now() - session.start_time).total_seconds()
                if elapsed > session.timeout_seconds:
                    logger.warning(f"Session {session_id} timeout")
                    session.status = "timeout"
                    break

                # 检查是否达成共识（通过分析消息）
                if await self._check_consensus(session_id):
                    logger.info(f"Session {session_id} reached consensus")
                    session.status = "completed"
                    break

                # 轮次间隔
                await asyncio.sleep(1)

            # 会话结束
            if session.status == "running":
                session.status = "completed"

            # 生成会话结果
            session.result = await self._generate_session_result(session_id)

            # 发送会话结束消息
            end_message = Message(
                type=MessageType.SESSION_END,
                sender="forum_engine",
                content=f"论坛会话结束: {session.status}",
                data={
                    "session_id": session_id,
                    "status": session.status,
                    "rounds": session.current_round,
                    "result": session.result
                }
            )
            await self.message_bus.publish(end_message)

            logger.info(f"Session {session_id} ended with status: {session.status}")

        except Exception as e:
            logger.error(f"Session {session_id} error: {e}")
            session.status = "error"
            session.result = {"error": str(e)}

        finally:
            # 停止监控
            await self.monitor.stop()

    async def _check_consensus(self, session_id: str) -> bool:
        """
        检查是否达成共识

        Args:
            session_id: 会话ID

        Returns:
            是否达成共识
        """
        # 获取最近的消息
        recent_messages = self.message_bus.get_messages(limit=20)

        # 统计共识关键词
        consensus_count = 0
        for msg in recent_messages:
            content_lower = msg.content.lower()
            if any(kw in content_lower for kw in ['agree', '同意', '一致', 'consensus', '达成']):
                consensus_count += 1

        # 简单策略：如果最近消息中有多个共识关键词，认为达成共识
        session = self.sessions[session_id]
        threshold = len(session.agents) * 0.5  # 至少一半Agent表示同意

        return consensus_count >= threshold

    async def _generate_session_result(self, session_id: str) -> Dict[str, Any]:
        """
        生成会话结果

        Args:
            session_id: 会话ID

        Returns:
            会话结果
        """
        session = self.sessions[session_id]
        messages = self.message_bus.get_messages()

        # 统计信息
        agent_message_counts = {}
        for msg in messages:
            if msg.sender not in agent_message_counts:
                agent_message_counts[msg.sender] = 0
            agent_message_counts[msg.sender] += 1

        # 获取讨论摘要
        summary = self.moderator.get_discussion_summary()

        # 使用LLM生成结论
        conclusion = await self._generate_conclusion(session_id, messages)

        return {
            "session_id": session_id,
            "topic": session.topic,
            "status": session.status,
            "total_rounds": session.current_round,
            "total_messages": len(messages),
            "agent_participation": agent_message_counts,
            "discussion_summary": summary,
            "conclusion": conclusion,
            "timestamp": datetime.now().isoformat()
        }

    async def _generate_conclusion(
        self,
        session_id: str,
        messages: List[Message]
    ) -> str:
        """
        使用LLM生成讨论结论

        Args:
            session_id: 会话ID
            messages: 消息列表

        Returns:
            结论文本
        """
        session = self.sessions[session_id]

        # 格式化消息历史
        message_text = []
        for msg in messages[-30:]:  # 只取最近30条消息
            message_text.append(f"{msg.sender}: {msg.content}")

        discussion_text = "\n".join(message_text)

        # 构建提示词
        prompt = f"""请总结以下Agent讨论的结论。

讨论主题：{session.topic}
参与Agent：{', '.join(session.agents)}
讨论轮次：{session.current_round}

讨论内容：
{discussion_text}

请提供：
1. 核心结论（2-3句话）
2. 主要观点总结
3. 是否达成共识
4. 未解决的问题（如有）

总结（300字以内）：
"""

        try:
            # 调用LLM
            if hasattr(self.llm, 'ainvoke'):
                response = await self.llm.ainvoke(prompt)
            else:
                response = self.llm.invoke(prompt)

            # 提取文本
            if hasattr(response, 'content'):
                conclusion = response.content
            elif isinstance(response, str):
                conclusion = response
            else:
                conclusion = str(response)

            return conclusion

        except Exception as e:
            logger.error(f"Failed to generate conclusion: {e}")
            return f"讨论结束，共进行 {session.current_round} 轮，涉及 {len(messages)} 条消息。"

    def get_session(self, session_id: str) -> Optional[ForumSession]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话对象
        """
        return self.sessions.get(session_id)

    def get_session_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        获取会话消息

        Args:
            session_id: 会话ID
            limit: 消息数量限制

        Returns:
            消息列表
        """
        # 过滤该会话的消息
        all_messages = self.message_bus.get_messages(limit=1000)
        session_messages = [
            msg for msg in all_messages
            if msg.data.get('session_id') == session_id
        ]

        if limit:
            return session_messages[-limit:]
        return session_messages

    async def stop_session(self, session_id: str):
        """
        停止会话

        Args:
            session_id: 会话ID
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return

        session = self.sessions[session_id]
        if session.status == "running":
            session.status = "stopped"
            logger.info(f"Session {session_id} stopped")

            # 发送停止消息
            stop_message = Message(
                type=MessageType.SESSION_END,
                sender="forum_engine",
                content="会话已停止",
                data={"session_id": session_id, "status": "stopped"}
            )
            await self.message_bus.publish(stop_message)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有会话

        Returns:
            会话列表
        """
        return [session.to_dict() for session in self.sessions.values()]

    async def broadcast_message(
        self,
        content: str,
        message_type: MessageType = MessageType.BROADCAST,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        广播消息到所有Agent

        Args:
            content: 消息内容
            message_type: 消息类型
            data: 附加数据
        """
        message = Message(
            type=message_type,
            sender="forum_engine",
            content=content,
            data=data or {}
        )
        await self.message_bus.publish(message)
        logger.info(f"Broadcasted message: {content[:50]}...")

    async def send_message_to_agent(
        self,
        agent_id: str,
        content: str,
        message_type: MessageType = MessageType.DIRECT_MESSAGE,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        发送消息到特定Agent

        Args:
            agent_id: 目标Agent ID
            content: 消息内容
            message_type: 消息类型
            data: 附加数据
        """
        message = Message(
            type=message_type,
            sender="forum_engine",
            content=content,
            data=data or {},
            recipients=[agent_id]
        )
        await self.message_bus.publish(message)
        logger.info(f"Sent message to {agent_id}: {content[:50]}...")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取引擎统计信息

        Returns:
            统计信息
        """
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s.status == "running")
        completed_sessions = sum(1 for s in self.sessions.values() if s.status == "completed")

        return {
            "total_agents": len(self.active_agents),
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "total_messages": len(self.message_bus.get_messages()),
            "active_agent_ids": list(self.active_agents.keys())
        }

    async def cleanup(self):
        """清理资源"""
        # 停止所有活动会话
        for session_id, session in self.sessions.items():
            if session.status == "running":
                await self.stop_session(session_id)

        # 停止监控
        await self.monitor.stop()

        logger.info("ForumEngine cleaned up")
