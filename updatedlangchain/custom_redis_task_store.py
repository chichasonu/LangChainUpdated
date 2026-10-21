# custom_redis_task_store.py
import redis
import json
import asyncio
from typing import Optional
from a2a.server.tasks.task_store import TaskStore
from a2a.server.context import ServerCallContext
from a2a.types.a2a_pb2 import Task, ListTasksRequest, ListTasksResponse
from google.protobuf.json_format import MessageToDict, DictToMessage
import logging

logger = logging.getLogger(__name__)

class CustomRedisTaskStore(TaskStore):
    """
    Custom Redis-backed TaskStore for persistent task storage.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "a2a:tasks:",
        ttl_seconds: Optional[int] = 3600,
    ):
        """
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            prefix: Key prefix for task storage
            ttl_seconds: Optional TTL for tasks in seconds
        """
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        
        # Create synchronous Redis client
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {host}:{port}/{db}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _task_to_dict(self, task: Task) -> dict:
        """Convert protobuf Task to dictionary for JSON storage."""
        return MessageToDict(task, preserving_proto_field_name=True)
    
    def _dict_to_task(self, task_dict: dict) -> Task:
        """Convert dictionary back to protobuf Task."""
        task = Task()
        DictToMessage(task_dict, task)
        return task
    
    async def save(self, task: Task, context: ServerCallContext) -> None:
        """Save or update a task in Redis."""
        task_id = task.id
        task_dict = self._task_to_dict(task)
        task_json = json.dumps(task_dict)
        
        # Store in Redis hash
        key = f"{self.prefix}{task_id}"
        self.redis_client.hset(key, "data", task_json)
        self.redis_client.hset(key, "updated_at", redis.commands.time()[0])
        
        # Set TTL if configured
        if self.ttl_seconds:
            self.redis_client.expire(key, self.ttl_seconds)
        
        logger.info(f"Task saved to Redis: {task_id}")
    
    async def get(self, task_id: str, context: ServerCallContext) -> Optional[Task]:
        """Retrieve a task by ID from Redis."""
        key = f"{self.prefix}{task_id}"
        
        # Get task data from Redis hash
        task_data = self.redis_client.hget(key, "data")
        
        if not task_data:
            logger.debug(f"Task not found in Redis: {task_id}")
            return None
        
        try:
            task_dict = json.loads(task_data)
            task = self._dict_to_task(task_dict)
            
            # Update TTL on access (slide the expiration)
            if self.ttl_seconds:
                self.redis_client.expire(key, self.ttl_seconds)
            
            logger.debug(f"Task retrieved from Redis: {task_id}")
            return task
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to deserialize task {task_id}: {e}")
            return None
    
    async def delete(self, task_id: str, context: ServerCallContext) -> None:
        """Delete a task by ID from Redis."""
        key = f"{self.prefix}{task_id}"
        self.redis_client.delete(key)
        logger.info(f"Task deleted from Redis: {task_id}")
    
    async def list(
        self, 
        params: ListTasksRequest, 
        context: ServerCallContext
    ) -> ListTasksResponse:
        """List tasks based on request parameters."""
        # Scan for all task keys
        pattern = f"{self.prefix}*"
        task_keys = self.redis_client.keys(pattern)
        
        tasks = []
        for key in task_keys:
            task_data = self.redis_client.hget(key, "data")
            if task_data:
                try:
                    task_dict = json.loads(task_data)
                    task = self._dict_to_task(task_dict)
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to deserialize task from {key}: {e}")
        
        # Apply pagination
        page_size = params.page_size or 50
        page_token = params.page_token or 0
        
        start_idx = int(page_token)
        end_idx = start_idx + page_size
        paginated_tasks = tasks[start_idx:end_idx]
        
        return ListTasksResponse(
            tasks=paginated_tasks,
            next_page_token=str(end_idx) if end_idx < len(tasks) else None
        )