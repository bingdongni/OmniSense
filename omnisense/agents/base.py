"""
Base Agent Class with LangChain Integration
提供所有智能体的基础能力和LangChain集成
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union
from enum import Enum

from pydantic import BaseModel, Field
from loguru import logger

# LangChain imports
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.language_models import BaseLLM
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOpenAI


class AgentRole(str, Enum):
    """Agent role definitions"""
    SCOUT = "scout"  # Data exploration and discovery
    ANALYST = "analyst"  # Deep data analysis
    ECOMMERCE = "ecommerce"  # E-commerce product analysis
    ACADEMIC = "academic"  # Academic research
    CREATOR = "creator"  # Content creation and optimization
    REPORT = "report"  # Report generation
    MANAGER = "manager"  # Agent orchestration


class AgentState(str, Enum):
    """Agent state"""
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentResponse(BaseModel):
    """Standardized agent response"""
    agent_name: str
    agent_role: AgentRole
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    reasoning: List[str] = Field(default_factory=list)  # Chain of thought
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentConfig(BaseModel):
    """Agent configuration"""
    name: str
    role: AgentRole
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3
    timeout: int = 300
    enable_memory: bool = True
    enable_cot: bool = True  # Chain of thought
    system_prompt: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base agent class with LangChain integration

    Features:
    - LangChain integration for LLM operations
    - Chain-of-thought reasoning
    - Structured output generation
    - Error handling and retry logic
    - Async support
    - Memory management
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.state = AgentState.IDLE
        self.llm = self._initialize_llm()
        self.memory = self._initialize_memory() if config.enable_memory else None
        self.chains: Dict[str, LLMChain] = {}
        self._setup_chains()

        # Forum collaboration support
        self.forum_queue: Optional[asyncio.Queue] = None
        self.forum_message_handler: Optional[asyncio.Task] = None
        self.in_forum: bool = False

        logger.info(f"Initialized {self.name} ({self.role.value}) agent")

    def _initialize_llm(self) -> BaseLLM:
        """Initialize LLM based on provider"""
        provider = self.config.llm_provider.lower()

        try:
            if provider == "ollama":
                return Ollama(
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    num_predict=self.config.max_tokens,
                )
            elif provider == "openai":
                from os import environ
                api_key = environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment")
                return ChatOpenAI(
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    api_key=api_key,
                )
            elif provider == "anthropic":
                from langchain_community.chat_models import ChatAnthropic
                from os import environ
                api_key = environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in environment")
                return ChatAnthropic(
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    api_key=api_key,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise

    def _initialize_memory(self) -> ConversationBufferMemory:
        """Initialize conversation memory"""
        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )

    @abstractmethod
    def _setup_chains(self):
        """Setup LangChain chains for the agent"""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get agent-specific system prompt"""
        pass

    def _create_chain(self, name: str, template: str, input_variables: List[str]) -> LLMChain:
        """Create a LangChain chain"""
        prompt = PromptTemplate(
            template=template,
            input_variables=input_variables
        )

        chain_kwargs = {
            "llm": self.llm,
            "prompt": prompt,
            "verbose": self.config.metadata.get("verbose", False)
        }

        if self.memory:
            chain_kwargs["memory"] = self.memory

        chain = LLMChain(**chain_kwargs)
        self.chains[name] = chain
        return chain

    async def _execute_with_retry(
        self,
        func,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        max_retries = max_retries or self.config.max_retries
        last_error = None

        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"{self.name} attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise last_error

    def _chain_of_thought(self, query: str, context: Dict[str, Any]) -> List[str]:
        """Generate chain-of-thought reasoning steps"""
        if not self.config.enable_cot:
            return []

        cot_prompt = f"""
Break down this task into clear reasoning steps:

Task: {query}
Context: {context}

Provide 3-5 clear reasoning steps:
"""
        try:
            response = self.llm.invoke(cot_prompt)
            steps = [s.strip() for s in response.split('\n') if s.strip() and s.strip()[0].isdigit()]
            return steps[:5]  # Limit to 5 steps
        except Exception as e:
            logger.warning(f"Chain-of-thought generation failed: {e}")
            return []

    def _extract_structured_output(
        self,
        response: str,
        schema: Type[BaseModel]
    ) -> Optional[BaseModel]:
        """Extract structured output from LLM response"""
        try:
            # Try to parse as JSON
            import json

            # Look for JSON in response
            start_idx = response.find('{')
            end_idx = response.rfind('}')

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx + 1]
                data = json.loads(json_str)
                return schema(**data)

            return None
        except Exception as e:
            logger.warning(f"Failed to extract structured output: {e}")
            return None

    async def think(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate reasoning steps for a query"""
        self.state = AgentState.THINKING
        context = context or {}

        try:
            reasoning_steps = await self._execute_with_retry(
                self._chain_of_thought,
                query,
                context
            )
            return reasoning_steps
        except Exception as e:
            logger.error(f"{self.name} thinking failed: {e}")
            return []
        finally:
            self.state = AgentState.IDLE

    @abstractmethod
    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a task and return structured response

        Args:
            task: Task parameters
            context: Additional context

        Returns:
            AgentResponse with results
        """
        pass

    async def collaborate(
        self,
        other_agent: "BaseAgent",
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Collaborate with another agent

        Args:
            other_agent: Agent to collaborate with
            task: Task parameters
            context: Shared context

        Returns:
            Combined agent response
        """
        self.state = AgentState.WAITING

        try:
            # Process task with both agents
            my_response = await self.process(task, context)
            other_response = await other_agent.process(task, context)

            # Combine responses
            combined_data = {
                self.name: my_response.data,
                other_agent.name: other_response.data
            }

            # Synthesize results
            synthesis_prompt = f"""
Synthesize the following agent responses:

Agent 1 ({self.name}): {my_response.message}
Agent 2 ({other_agent.name}): {other_response.message}

Provide a unified response:
"""
            synthesis = await self._execute_with_retry(
                self.llm.ainvoke,
                synthesis_prompt
            )

            return AgentResponse(
                agent_name=f"{self.name}+{other_agent.name}",
                agent_role=self.role,
                success=my_response.success and other_response.success,
                data=combined_data,
                message=synthesis,
                reasoning=my_response.reasoning + other_response.reasoning,
                confidence=(my_response.confidence + other_response.confidence) / 2,
                metadata={
                    "collaboration": True,
                    "agents": [self.name, other_agent.name]
                }
            )
        except Exception as e:
            logger.error(f"Collaboration failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def join_forum(self, forum_queue: asyncio.Queue):
        """
        Join a forum session

        Args:
            forum_queue: Message queue from ForumEngine
        """
        self.forum_queue = forum_queue
        self.in_forum = True

        # Start message handler
        self.forum_message_handler = asyncio.create_task(
            self._handle_forum_messages()
        )

        logger.info(f"{self.name} joined forum")

    async def leave_forum(self):
        """Leave the forum session"""
        self.in_forum = False

        if self.forum_message_handler:
            self.forum_message_handler.cancel()
            try:
                await self.forum_message_handler
            except asyncio.CancelledError:
                pass
            self.forum_message_handler = None

        self.forum_queue = None
        logger.info(f"{self.name} left forum")

    async def _handle_forum_messages(self):
        """Handle incoming forum messages"""
        if not self.forum_queue:
            return

        try:
            while self.in_forum:
                # Get message from queue
                message = await asyncio.wait_for(
                    self.forum_queue.get(),
                    timeout=1.0
                )

                # Process forum message
                await self._process_forum_message(message)

        except asyncio.TimeoutError:
            # No message, continue
            if self.in_forum:
                await self._handle_forum_messages()
        except asyncio.CancelledError:
            logger.info(f"{self.name} forum message handler cancelled")
        except Exception as e:
            logger.error(f"{self.name} forum message handler error: {e}")

    async def _process_forum_message(self, message):
        """
        Process a forum message (to be overridden by subclasses)

        Args:
            message: Message from forum
        """
        logger.debug(f"{self.name} received forum message: {message.type.value}")

        # Default handling based on message type
        from omnisense.forum import MessageType

        if message.type == MessageType.SESSION_START:
            logger.info(f"{self.name} session started: {message.data.get('topic')}")

        elif message.type == MessageType.ROUND_START:
            # Generate response for this round
            await self._generate_forum_response(message)

        elif message.type == MessageType.AGENT_MESSAGE:
            # Process other agent's message
            logger.info(f"{self.name} received message from {message.sender}")

        elif message.type == MessageType.MODERATOR_GUIDANCE:
            # Process moderator guidance
            logger.info(f"{self.name} received moderator guidance")

        elif message.type == MessageType.CONSENSUS_REQUEST:
            # Respond to consensus request
            await self._respond_to_consensus_request(message)

        elif message.type == MessageType.SESSION_END:
            logger.info(f"{self.name} session ended")

    async def _generate_forum_response(self, round_message):
        """
        Generate a response for a forum round

        Args:
            round_message: Round start message
        """
        try:
            # Get recent messages for context
            session_id = round_message.data.get('session_id')
            round_num = round_message.data.get('round')

            # Generate response based on agent's perspective
            response_prompt = f"""
You are {self.name}, an AI agent with role {self.role.value}.

Current discussion round: {round_num}

Based on your role and expertise, provide your perspective on the ongoing discussion.
Be concise (2-3 sentences) and constructive.
"""

            response_text = await self._execute_with_retry(
                self.llm.ainvoke,
                response_prompt
            )

            # Send response to forum (import here to avoid circular dependency)
            from omnisense.forum import Message, MessageType

            response_message = Message(
                type=MessageType.AGENT_MESSAGE,
                sender=self.name,
                content=response_text if isinstance(response_text, str) else str(response_text),
                data={
                    "session_id": session_id,
                    "round": round_num,
                    "agent_role": self.role.value
                }
            )

            # Note: In actual implementation, agent would have reference to message_bus
            # For now, this shows the structure
            logger.info(f"{self.name} generated forum response")

        except Exception as e:
            logger.error(f"{self.name} failed to generate forum response: {e}")

    async def _respond_to_consensus_request(self, message):
        """
        Respond to a consensus request

        Args:
            message: Consensus request message
        """
        topic = message.data.get('topic', 'the topic')

        # Generate consensus response
        consensus_prompt = f"""
You are {self.name}, an AI agent with role {self.role.value}.

A consensus is being requested on: {topic}

Do you agree or disagree? Provide a brief reasoning (1-2 sentences).
"""

        try:
            response = await self._execute_with_retry(
                self.llm.ainvoke,
                consensus_prompt
            )

            logger.info(f"{self.name} responded to consensus request")

        except Exception as e:
            logger.error(f"{self.name} failed to respond to consensus request: {e}")

    def reset(self):
        """Reset agent state"""
        self.state = AgentState.IDLE
        if self.memory:
            self.memory.clear()
        logger.info(f"Reset {self.name} agent")

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.name,
            "role": self.role.value,
            "state": self.state.value,
            "config": self.config.dict(),
            "memory_size": len(self.memory.buffer) if self.memory else 0
        }
