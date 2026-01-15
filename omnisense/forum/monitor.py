#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forum Monitor

监控Agent日志和活动，识别关键事件
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
from loguru import logger

from .message_bus import MessageBus, Message, MessageType


class EventType(str, Enum):
    """事件类型"""
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    DISAGREEMENT = "disagreement"
    CONSENSUS = "consensus"
    QUESTION_RAISED = "question_raised"
    INSIGHT_FOUND = "insight_found"


class ForumMonitor:
    """论坛监控器"""

    def __init__(self, message_bus: MessageBus, config: Optional[Dict[str, Any]] = None):
        """
        初始化监控器

        Args:
            message_bus: 消息总线
            config: 配置
        """
        self.message_bus = message_bus
        self.config = config or {}
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.is_running = False

        # 订阅消息
        self._subscribe_to_messages()

        logger.info("ForumMonitor initialized")

    def _subscribe_to_messages(self):
        """订阅消息总线"""
        self.message_bus.subscribe(MessageType.TASK_START, self._on_task_start)
        self.message_bus.subscribe(MessageType.TASK_COMPLETE, self._on_task_complete)
        self.message_bus.subscribe(MessageType.TASK_FAILED, self._on_task_failed)
        self.message_bus.subscribe(MessageType.AGENT_MESSAGE, self._on_agent_message)

    async def _on_task_start(self, message: Message):
        """处理任务开始事件"""
        logger.info(f"Task started: {message.sender}")
        await self._emit_event(EventType.AGENT_STARTED, message)

    async def _on_task_complete(self, message: Message):
        """处理任务完成事件"""
        logger.info(f"Task completed: {message.sender}")
        await self._emit_event(EventType.AGENT_COMPLETED, message)

    async def _on_task_failed(self, message: Message):
        """处理任务失败事件"""
        logger.warning(f"Task failed: {message.sender}")
        await self._emit_event(EventType.AGENT_FAILED, message)

    async def _on_agent_message(self, message: Message):
        """处理Agent消息"""
        # 分析消息内容，识别特殊事件
        content = message.content.lower()

        if any(keyword in content for keyword in ['disagree', '不同意', '反对']):
            await self._emit_event(EventType.DISAGREEMENT, message)

        if any(keyword in content for keyword in ['agree', '同意', '一致']):
            await self._emit_event(EventType.CONSENSUS, message)

        if any(keyword in content for keyword in ['question', '问题', '疑问']):
            await self._emit_event(EventType.QUESTION_RAISED, message)

        if any(keyword in content for keyword in ['insight', '发现', '洞察']):
            await self._emit_event(EventType.INSIGHT_FOUND, message)

    async def _emit_event(self, event_type: EventType, message: Message):
        """发射事件"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

    def on_event(self, event_type: EventType, handler: Callable):
        """
        注册事件处理器

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Event handler registered for {event_type}")

    def get_recent_events(self, event_type: Optional[EventType] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取最近的事件

        Args:
            event_type: 事件类型过滤
            limit: 返回数量限制

        Returns:
            事件列表
        """
        messages = self.message_bus.get_messages(limit=limit)
        events = []

        for msg in messages:
            events.append({
                'type': msg.type.value,
                'sender': msg.sender,
                'content': msg.content,
                'timestamp': msg.timestamp,
            })

        return events[-limit:]

    async def start(self):
        """启动监控"""
        self.is_running = True
        logger.info("ForumMonitor started")

    async def stop(self):
        """停止监控"""
        self.is_running = False
        logger.info("ForumMonitor stopped")
