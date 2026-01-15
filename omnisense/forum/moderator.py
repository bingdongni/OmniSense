#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Moderator

基于LLM的智能主持人，引导Agent讨论和达成共识
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from .message_bus import MessageBus, Message, MessageType
from .monitor import ForumMonitor, EventType


class LLMModerator:
    """LLM主持人"""

    def __init__(
        self,
        llm,
        message_bus: MessageBus,
        monitor: ForumMonitor,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化主持人

        Args:
            llm: LLM实例
            message_bus: 消息总线
            monitor: 论坛监控器
            config: 配置
        """
        self.llm = llm
        self.message_bus = message_bus
        self.monitor = monitor
        self.config = config or {}

        # 注册事件处理
        self._register_event_handlers()

        logger.info("LLMModerator initialized")

    def _register_event_handlers(self):
        """注册事件处理器"""
        self.monitor.on_event(EventType.DISAGREEMENT, self._on_disagreement)
        self.monitor.on_event(EventType.QUESTION_RAISED, self._on_question)
        self.monitor.on_event(EventType.CONSENSUS, self._on_consensus)

    async def _on_disagreement(self, message: Message):
        """处理分歧事件"""
        logger.info(f"Disagreement detected from {message.sender}")

        # 生成引导性建议
        guidance = await self._generate_guidance(
            event_type="disagreement",
            context=message
        )

        # 发布主持人引导消息
        await self._publish_guidance(guidance)

    async def _on_question(self, message: Message):
        """处理问题事件"""
        logger.info(f"Question raised from {message.sender}")

        # 生成引导性建议
        guidance = await self._generate_guidance(
            event_type="question",
            context=message
        )

        # 发布主持人引导消息
        await self._publish_guidance(guidance)

    async def _on_consensus(self, message: Message):
        """处理共识事件"""
        logger.info(f"Consensus detected from {message.sender}")

        # 生成引导性建议
        guidance = await self._generate_guidance(
            event_type="consensus",
            context=message
        )

        # 发布主持人引导消息
        await self._publish_guidance(guidance)

    async def _generate_guidance(
        self,
        event_type: str,
        context: Message
    ) -> str:
        """
        生成引导性建议

        Args:
            event_type: 事件类型 (disagreement/question/consensus)
            context: 上下文消息

        Returns:
            引导性建议文本
        """
        # 获取最近的讨论历史
        recent_messages = self.message_bus.get_messages(limit=10)
        discussion_context = self._format_discussion_context(recent_messages)

        # 构建提示词
        prompt = self._build_guidance_prompt(
            event_type=event_type,
            current_message=context,
            discussion_context=discussion_context
        )

        try:
            # 调用LLM生成引导
            if hasattr(self.llm, 'ainvoke'):
                response = await self.llm.ainvoke(prompt)
            elif hasattr(self.llm, 'agenerate'):
                response = await self.llm.agenerate([prompt])
                response = response.generations[0][0].text
            else:
                # 同步调用的fallback
                response = self.llm.invoke(prompt)

            # 提取文本内容
            if hasattr(response, 'content'):
                guidance = response.content
            elif isinstance(response, str):
                guidance = response
            else:
                guidance = str(response)

            logger.debug(f"Generated guidance for {event_type}: {guidance[:100]}...")
            return guidance

        except Exception as e:
            logger.error(f"Failed to generate guidance: {e}")
            return self._get_fallback_guidance(event_type)

    def _format_discussion_context(self, messages: List[Message]) -> str:
        """
        格式化讨论上下文

        Args:
            messages: 消息列表

        Returns:
            格式化的讨论历史
        """
        if not messages:
            return "暂无讨论历史"

        context_lines = []
        for msg in messages:
            context_lines.append(
                f"[{msg.timestamp}] {msg.sender} ({msg.type.value}): {msg.content[:200]}"
            )

        return "\n".join(context_lines)

    def _build_guidance_prompt(
        self,
        event_type: str,
        current_message: Message,
        discussion_context: str
    ) -> str:
        """
        构建引导提示词

        Args:
            event_type: 事件类型
            current_message: 当前消息
            discussion_context: 讨论上下文

        Returns:
            提示词文本
        """
        base_prompt = f"""你是一个智能论坛主持人，负责引导多个AI Agent进行有效讨论和协作。

当前讨论历史：
{discussion_context}

当前事件类型：{event_type}
当前消息来自：{current_message.sender}
消息内容：{current_message.content}
"""

        if event_type == "disagreement":
            prompt = base_prompt + """
检测到Agent之间存在分歧。请分析分歧的核心点，并提供建设性的引导建议：
1. 总结双方的主要观点
2. 识别分歧的根本原因
3. 提出可能的折中方案或进一步探讨的方向
4. 鼓励Agent提供更多证据支持各自观点

请以简洁、中立的方式给出引导建议（200字以内）：
"""

        elif event_type == "question":
            prompt = base_prompt + """
检测到Agent提出了问题。请分析问题的性质，并提供引导建议：
1. 判断问题是否需要其他Agent回答
2. 识别哪些Agent最适合回答这个问题
3. 建议问题的探讨方向
4. 如果问题不清晰，建议如何澄清

请以简洁的方式给出引导建议（150字以内）：
"""

        elif event_type == "consensus":
            prompt = base_prompt + """
检测到Agent之间可能达成了共识。请分析并确认：
1. 总结达成的共识内容
2. 确认是否所有相关Agent都同意
3. 建议下一步行动
4. 如果共识不完整，指出需要进一步讨论的点

请以简洁的方式给出引导建议（150字以内）：
"""

        else:
            prompt = base_prompt + "\n请分析当前讨论状态，并给出引导建议（150字以内）："

        return prompt

    def _get_fallback_guidance(self, event_type: str) -> str:
        """
        获取备用引导建议（当LLM调用失败时）

        Args:
            event_type: 事件类型

        Returns:
            备用建议文本
        """
        fallback_messages = {
            "disagreement": "检测到分歧。建议各Agent提供更多证据支持各自观点，并尝试找到共同点。",
            "question": "检测到问题。建议相关Agent提供回答，并分享各自的见解。",
            "consensus": "检测到可能的共识。建议确认所有Agent的意见，并总结达成的结论。",
        }

        return fallback_messages.get(
            event_type,
            "请继续讨论，并分享更多见解。"
        )

    async def _publish_guidance(self, guidance: str):
        """
        发布主持人引导消息

        Args:
            guidance: 引导建议文本
        """
        guidance_message = Message(
            type=MessageType.MODERATOR_GUIDANCE,
            sender="moderator",
            content=guidance,
            data={"role": "moderator"}
        )

        await self.message_bus.publish(guidance_message)
        logger.info(f"Published moderator guidance: {guidance[:100]}...")

    async def request_consensus(
        self,
        topic: str,
        agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        主动请求Agent达成共识

        Args:
            topic: 讨论主题
            agents: 目标Agent列表（None表示所有Agent）

        Returns:
            共识请求结果
        """
        logger.info(f"Requesting consensus on topic: {topic}")

        # 构建共识请求消息
        request_message = Message(
            type=MessageType.CONSENSUS_REQUEST,
            sender="moderator",
            content=f"请就以下主题达成共识：{topic}",
            data={"topic": topic},
            recipients=agents
        )

        await self.message_bus.publish(request_message)

        return {
            "status": "requested",
            "topic": topic,
            "target_agents": agents or "all"
        }

    def get_discussion_summary(self) -> Dict[str, Any]:
        """
        获取讨论摘要

        Returns:
            讨论统计信息
        """
        messages = self.message_bus.get_messages(limit=100)

        # 统计各类事件
        event_counts = {
            "disagreements": 0,
            "questions": 0,
            "consensus": 0,
            "total_messages": len(messages)
        }

        agent_participation = {}

        for msg in messages:
            # 统计Agent参与度
            if msg.sender not in agent_participation:
                agent_participation[msg.sender] = 0
            agent_participation[msg.sender] += 1

            # 统计事件类型（简单关键词匹配）
            content_lower = msg.content.lower()
            if any(kw in content_lower for kw in ['disagree', '不同意', '反对']):
                event_counts["disagreements"] += 1
            if any(kw in content_lower for kw in ['question', '问题', '疑问']):
                event_counts["questions"] += 1
            if any(kw in content_lower for kw in ['agree', '同意', '一致']):
                event_counts["consensus"] += 1

        return {
            "event_counts": event_counts,
            "agent_participation": agent_participation,
            "most_active_agent": max(agent_participation.items(), key=lambda x: x[1])[0] if agent_participation else None
        }
