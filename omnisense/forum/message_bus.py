#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Message Bus

Agent间消息传递系统
"""

import asyncio
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger


class MessageType(str, Enum):
    """消息类型"""
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    AGENT_MESSAGE = "agent_message"
    MODERATOR_GUIDANCE = "moderator_guidance"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_RESPONSE = "consensus_response"
    SYSTEM_EVENT = "system_event"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ROUND_START = "round_start"
    BROADCAST = "broadcast"
    DIRECT_MESSAGE = "direct_message"


@dataclass
class Message:
    """消息对象"""
    type: MessageType
    sender: str
    content: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    recipients: Optional[List[str]] = None  # None表示广播
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'type': self.type.value,
            'sender': self.sender,
            'content': self.content,
            'data': self.data,
            'timestamp': self.timestamp,
            'recipients': self.recipients,
            'metadata': self.metadata,
        }


class MessageBus:
    """消息总线"""

    def __init__(self, max_history: int = 1000):
        """
        初始化消息总线

        Args:
            max_history: 最大历史消息数
        """
        self.max_history = max_history
        self.messages: List[Message] = []
        self.subscribers: Dict[str, List[Callable]] = {}
        self.agent_queues: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

        logger.info("MessageBus initialized")

    async def publish(self, message: Message):
        """
        发布消息

        Args:
            message: 消息对象
        """
        async with self._lock:
            # 添加到历史
            self.messages.append(message)
            if len(self.messages) > self.max_history:
                self.messages.pop(0)

            logger.debug(f"Message published: {message.type} from {message.sender}")

            # 分发给订阅者
            await self._dispatch_to_subscribers(message)

            # 分发给Agent队列
            await self._dispatch_to_agents(message)

    async def _dispatch_to_subscribers(self, message: Message):
        """分发给订阅者"""
        message_type = message.type.value
        if message_type in self.subscribers:
            for callback in self.subscribers[message_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")

    async def _dispatch_to_agents(self, message: Message):
        """分发给Agent队列"""
        if message.recipients is None:
            # 广播给所有Agent
            for agent_id, queue in self.agent_queues.items():
                if agent_id != message.sender:
                    await queue.put(message)
        else:
            # 发送给指定Agent
            for agent_id in message.recipients:
                if agent_id in self.agent_queues:
                    await self.agent_queues[agent_id].put(message)

    def subscribe(self, message_type: MessageType, callback: Callable):
        """
        订阅消息类型

        Args:
            message_type: 消息类型
            callback: 回调函数
        """
        type_key = message_type.value
        if type_key not in self.subscribers:
            self.subscribers[type_key] = []
        self.subscribers[type_key].append(callback)
        logger.debug(f"Subscribed to {message_type}")

    def unsubscribe(self, message_type: MessageType, callback: Callable):
        """取消订阅"""
        type_key = message_type.value
        if type_key in self.subscribers:
            self.subscribers[type_key].remove(callback)

    def register_agent(self, agent_id: str) -> asyncio.Queue:
        """
        注册Agent

        Args:
            agent_id: Agent ID

        Returns:
            Agent的消息队列
        """
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.Queue()
            logger.info(f"Agent registered: {agent_id}")
        return self.agent_queues[agent_id]

    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.agent_queues:
            del self.agent_queues[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")

    def get_messages(
        self,
        message_type: Optional[MessageType] = None,
        sender: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        获取历史消息

        Args:
            message_type: 消息类型过滤
            sender: 发送者过滤
            limit: 返回数量限制

        Returns:
            消息列表
        """
        filtered = self.messages

        if message_type:
            filtered = [m for m in filtered if m.type == message_type]

        if sender:
            filtered = [m for m in filtered if m.sender == sender]

        return filtered[-limit:]

    def clear_history(self):
        """清空历史消息"""
        self.messages.clear()
        logger.info("Message history cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_messages': len(self.messages),
            'registered_agents': len(self.agent_queues),
            'subscribers': {k: len(v) for k, v in self.subscribers.items()},
        }

