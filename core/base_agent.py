"""
core/base_agent.py — Enhanced BaseAgent with Memory & Multi-User Support

Features:
- Skill Memory: Stores successful tool executions for learning
- Failure Memory: Logs errors to avoid repeating mistakes
- Multi-User Separation: All operations scoped by user_id
- Redis Integration: Fast caching and state management
- PostgreSQL Integration: Persistent memory storage
"""
from __future__ import annotations
import os
import json
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta

# Database clients (to be implemented in libs/)
try:
    from libs.storage.postgres import PostgreSQLClient
    from libs.storage.redis import RedisClient
except ImportError:
    # Fallback for development
    PostgreSQLClient = None
    RedisClient = None

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context for agent execution with user separation"""
    user_id: str                              # Unique user identifier
    session_id: str                           # Session identifier
    task_id: Optional[str] = None            # Task queue ID
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "metadata": self.metadata,
        }


@dataclass
class AgentResult:
    """Result of agent execution"""
    ok: bool = False
    answer: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: float = 0.0
    steps_log: List[Dict] = field(default_factory=list)
    memory_used: int = 0                     # Number of memories used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "answer": self.answer[:2000],     # Truncate for API
            "data": self.data,
            "error": self.error,
            "duration": round(self.duration, 2),
            "steps": len(self.steps_log),
            "memory_used": self.memory_used,
        }


@dataclass
class SkillMemory:
    """Represents a successful tool execution"""
    user_id: str
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Any
    timestamp: datetime
    success_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "timestamp": self.timestamp.isoformat(),
            "success_count": self.success_count,
        }


@dataclass
class FailureMemory:
    """Represents a failed tool execution"""
    user_id: str
    tool_name: str
    error_message: str
    input_params: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "error_message": self.error_message,
            "input_params": self.input_params,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
        }


class MemoryManager:
    """
    Manages skill and failure memory for agents
    Supports multi-user separation and persistence
    """

    def __init__(self, postgres_client: Optional[Any] = None,
                 redis_client: Optional[Any] = None):
        self.postgres = postgres_client
        self.redis = redis_client
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema if needed"""
        if not self.postgres:
            return

        schema_sql = """
        -- Skill Memory Table
        CREATE TABLE IF NOT EXISTS skill_memory (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            tool_name VARCHAR(255) NOT NULL,
            input_params JSONB NOT NULL,
            output_result JSONB,
            timestamp TIMESTAMP DEFAULT NOW(),
            success_count INTEGER DEFAULT 1,
            INDEX idx_user_tool (user_id, tool_name),
            INDEX idx_timestamp (timestamp)
        );

        -- Failure Memory Table
        CREATE TABLE IF NOT EXISTS failure_memory (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            tool_name VARCHAR(255) NOT NULL,
            error_message TEXT NOT NULL,
            input_params JSONB NOT NULL,
            timestamp TIMESTAMP DEFAULT NOW(),
            retry_count INTEGER DEFAULT 0,
            INDEX idx_user_tool (user_id, tool_name),
            INDEX idx_timestamp (timestamp)
        );

        -- User Statistics Table
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id VARCHAR(255) PRIMARY KEY,
            total_tasks INTEGER DEFAULT 0,
            successful_tasks INTEGER DEFAULT 0,
            failed_tasks INTEGER DEFAULT 0,
            total_tools_used INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """

        try:
            self.postgres.execute(schema_sql)
            logger.info("Memory schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory schema: {e}")

    def store_skill(self, context: AgentContext, tool_name: str,
                   input_params: Dict, output_result: Any) -> bool:
        """Store successful tool execution in skill memory"""
        try:
            memory = SkillMemory(
                user_id=context.user_id,
                tool_name=tool_name,
                input_params=input_params,
                output_result=output_result,
                timestamp=datetime.now()
            )

            # Store in PostgreSQL for persistence
            if self.postgres:
                self.postgres.execute(
                    """
                    INSERT INTO skill_memory
                    (user_id, tool_name, input_params, output_result, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, tool_name, input_params)
                    DO UPDATE SET
                        success_count = skill_memory.success_count + 1,
                        timestamp = EXCLUDED.timestamp
                    """,
                    (memory.user_id, memory.tool_name,
                     json.dumps(memory.input_params),
                     json.dumps(memory.output_result),
                     memory.timestamp)
                )

            # Cache in Redis for fast access
            if self.redis:
                cache_key = f"skill:{context.user_id}:{tool_name}"
                self.redis.lpush(cache_key, json.dumps(memory.to_dict()))
                self.redis.ltrim(cache_key, 0, 99)  # Keep last 100
                self.redis.expire(cache_key, 86400 * 7)  # 7 days

            logger.info(f"Stored skill memory: {tool_name} for user {context.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store skill memory: {e}")
            return False

    def store_failure(self, context: AgentContext, tool_name: str,
                     error_message: str, input_params: Dict) -> bool:
        """Store failed tool execution in failure memory"""
        try:
            memory = FailureMemory(
                user_id=context.user_id,
                tool_name=tool_name,
                error_message=error_message,
                input_params=input_params,
                timestamp=datetime.now()
            )

            # Store in PostgreSQL
            if self.postgres:
                self.postgres.execute(
                    """
                    INSERT INTO failure_memory
                    (user_id, tool_name, error_message, input_params, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (memory.user_id, memory.tool_name, memory.error_message,
                     json.dumps(memory.input_params), memory.timestamp)
                )

            # Cache in Redis
            if self.redis:
                cache_key = f"failure:{context.user_id}:{tool_name}"
                self.redis.lpush(cache_key, json.dumps(memory.to_dict()))
                self.redis.ltrim(cache_key, 0, 49)  # Keep last 50
                self.redis.expire(cache_key, 86400 * 3)  # 3 days

            logger.warning(f"Stored failure memory: {tool_name} for user {context.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store failure memory: {e}")
            return False

    def get_similar_skills(self, context: AgentContext, tool_name: str,
                          limit: int = 5) -> List[SkillMemory]:
        """Retrieve similar successful executions from memory"""
        skills = []

        try:
            # Try Redis cache first
            if self.redis:
                cache_key = f"skill:{context.user_id}:{tool_name}"
                cached = self.redis.lrange(cache_key, 0, limit - 1)
                if cached:
                    for item in cached:
                        data = json.loads(item)
                        skills.append(SkillMemory(
                            user_id=data["user_id"],
                            tool_name=data["tool_name"],
                            input_params=data["input_params"],
                            output_result=data["output_result"],
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            success_count=data.get("success_count", 1)
                        ))
                    return skills

            # Fallback to PostgreSQL
            if self.postgres:
                rows = self.postgres.query(
                    """
                    SELECT * FROM skill_memory
                    WHERE user_id = %s AND tool_name = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (context.user_id, tool_name, limit)
                )

                for row in rows:
                    skills.append(SkillMemory(
                        user_id=row["user_id"],
                        tool_name=row["tool_name"],
                        input_params=json.loads(row["input_params"]),
                        output_result=json.loads(row["output_result"]) if row["output_result"] else None,
                        timestamp=row["timestamp"],
                        success_count=row.get("success_count", 1)
                    ))

        except Exception as e:
            logger.error(f"Failed to retrieve skills: {e}")

        return skills

    def get_recent_failures(self, context: AgentContext, tool_name: str,
                           hours: int = 24) -> List[FailureMemory]:
        """Retrieve recent failures to avoid repeating mistakes"""
        failures = []
        cutoff = datetime.now() - timedelta(hours=hours)

        try:
            if self.postgres:
                rows = self.postgres.query(
                    """
                    SELECT * FROM failure_memory
                    WHERE user_id = %s AND tool_name = %s
                    AND timestamp > %s
                    ORDER BY timestamp DESC
                    """,
                    (context.user_id, tool_name, cutoff)
                )

                for row in rows:
                    failures.append(FailureMemory(
                        user_id=row["user_id"],
                        tool_name=row["tool_name"],
                        error_message=row["error_message"],
                        input_params=json.loads(row["input_params"]),
                        timestamp=row["timestamp"],
                        retry_count=row.get("retry_count", 0)
                    ))

        except Exception as e:
            logger.error(f"Failed to retrieve failures: {e}")

        return failures


class BaseAgent(ABC):
    """
    Enhanced Base Agent with Memory and Multi-User Support

    All agents should inherit from this class and implement:
    - execute(context, task) method
    """

    NAME: str = "base"
    EMOJI: str = "🤖"
    DESCRIPTION: str = "Base agent class"
    VERSION: str = "1.0.0"

    def __init__(self, postgres_client: Optional[Any] = None,
                 redis_client: Optional[Any] = None):
        self.memory = MemoryManager(postgres_client, redis_client)
        self.status_callback: Optional[Callable] = None
        self._tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        """Register a tool that this agent can use"""
        self._tools[name] = func
        logger.info(f"[{self.NAME}] Registered tool: {name}")

    def set_status_callback(self, callback: Callable):
        """Set callback for status updates"""
        self.status_callback = callback

    def update_status(self, message: str):
        """Send status update to callback if available"""
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                logger.error(f"Status callback failed: {e}")

    @abstractmethod
    def execute(self, context: AgentContext, task: str,
                **kwargs) -> AgentResult:
        """
        Execute agent task with given context
        Must be implemented by subclasses
        """
        pass

    def execute_tool(self, context: AgentContext, tool_name: str,
                    **params) -> Any:
        """
        Execute a tool with memory tracking

        - Checks failure memory to avoid repeating mistakes
        - Checks skill memory for similar successful executions
        - Stores result in appropriate memory
        """
        start_time = time.time()

        # Check if tool exists
        if tool_name not in self._tools:
            error = f"Tool '{tool_name}' not found"
            logger.error(error)
            return {"ok": False, "error": error}

        # Check recent failures
        recent_failures = self.memory.get_recent_failures(context, tool_name, hours=24)
        if len(recent_failures) >= 3:
            logger.warning(f"Tool '{tool_name}' has {len(recent_failures)} recent failures")
            # Optionally skip or warn user

        # Check for similar successful executions
        similar_skills = self.memory.get_similar_skills(context, tool_name, limit=3)
        if similar_skills:
            logger.info(f"Found {len(similar_skills)} similar successful executions")
            # Could use this to optimize parameters

        # Execute the tool
        try:
            self.update_status(f"Executing tool: {tool_name}")
            result = self._tools[tool_name](**params)

            # Store in skill memory on success
            self.memory.store_skill(context, tool_name, params, result)

            duration = time.time() - start_time
            logger.info(f"Tool '{tool_name}' executed successfully in {duration:.2f}s")

            return result

        except Exception as e:
            # Store in failure memory
            error_msg = str(e)
            self.memory.store_failure(context, tool_name, error_msg, params)

            duration = time.time() - start_time
            logger.error(f"Tool '{tool_name}' failed after {duration:.2f}s: {error_msg}")

            return {"ok": False, "error": error_msg}

    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.NAME,
            "emoji": self.EMOJI,
            "description": self.DESCRIPTION,
            "version": self.VERSION,
            "tools": list(self._tools.keys()),
        }


# Example implementation
class ExampleAgent(BaseAgent):
    """Example agent implementation"""

    NAME = "example"
    EMOJI = "📝"
    DESCRIPTION = "Example agent for demonstration"

    def execute(self, context: AgentContext, task: str, **kwargs) -> AgentResult:
        """Execute example task"""
        start_time = time.time()
        result = AgentResult()

        try:
            self.update_status(f"Processing task for user {context.user_id}")

            # Simulate work
            time.sleep(0.5)

            result.ok = True
            result.answer = f"Task completed: {task}"
            result.duration = time.time() - start_time

        except Exception as e:
            result.ok = False
            result.error = str(e)
            result.duration = time.time() - start_time

        return result


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Create agent
    agent = ExampleAgent()

    # Create context
    context = AgentContext(
        user_id="user_123",
        session_id="session_456"
    )

    # Execute task
    result = agent.execute(context, "Test task")
    print(json.dumps(result.to_dict(), indent=2))
